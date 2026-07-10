import base64
import io
import logging
from typing import Optional

import cv2
import numpy as np

from app.agents.verification.schemas.schemas import FraudDetectionRequest, FraudDetectionResponse
from app.agents.verification.core.exceptions import FraudDetectionError
from app.agents.verification.core.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
BLUR_LAPLACIAN_THRESHOLD = 80.0   # below = blurry image
OVEREXPOSURE_THRESHOLD = 220      # pixel value for overexposed
OVEREXPOSURE_FRACTION = 0.20      # >20% pixels overexposed → flag (relaxed from 15%)

# Document types that DO carry a photograph — face detection ONLY runs for these.
# All other doc types (income certs, bank passbooks, domicile certs, etc.) are
# text-only and will never have a face — skip face check to avoid false flags.
_PHOTO_BEARING_DOC_TYPES = {"PASSPORT", "DRIVING_LICENSE", "DL"}

# Multiple cascades tried in priority order
FACE_CASCADE_PATHS = [
    cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml",
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
    cv2.data.haarcascades + "haarcascade_frontalface_alt.xml",
]


import uuid

class FraudDetectionService:
    """
    OpenCV-only fraud signal detector.
    All checks are done in-process; no external API calls.
    """

    def __init__(self):
        # Cascades are loaded lazily inside _check_face_presence
        pass

    @staticmethod
    def detect(image_path: str, doc_type: str = "") -> dict:
        service = FraudDetectionService()
        request = FraudDetectionRequest(image_path=image_path)
        res = service.detect_request(request, doc_type=doc_type)
        return res.model_dump()

    def detect_request(
        self,
        request: FraudDetectionRequest,
        doc_type: str = "",
    ) -> FraudDetectionResponse:
        doc_type_upper = (doc_type or "").upper()
        logger.info(
            f"Starting fraud detection on path: {request.image_path} "
            f"(doc_type={doc_type_upper or 'unknown'})"
        )

        image_path = request.image_path or ""
        if not image_path:
            raise FraudDetectionError("No image_path provided for fraud detection")

        try:
            img_bgr = cv2.imread(image_path)
            if img_bgr is None:
                raise ValueError("cv2.imread returned None — unable to load image")
        except Exception as e:
            raise FraudDetectionError(f"Image load failed: {e}")

        img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        signals = {}
        fraud_flags = []

        # Signal 1: Blur — genuine quality issue; low Laplacian variance
        blur_result = self._check_blur(img_gray)
        signals["blur"] = blur_result
        if blur_result["flagged"]:
            fraud_flags.append("BLUR")

        # Signal 2: Over-exposure — severe brightness washing out document text
        over_result = self._check_overexposure(img_gray)
        signals["overexposure"] = over_result
        if over_result["flagged"]:
            fraud_flags.append("OVER_EXPOSURE")

        # Signal 3: Face presence — ONLY for known photo-bearing documents.
        # Any doc type not in _PHOTO_BEARING_DOC_TYPES is treated as text-only
        # (Income Certificate, Bank Passbook, Domicile Certificate, PAN, Aadhaar, etc.)
        is_photo_doc = doc_type_upper in _PHOTO_BEARING_DOC_TYPES
        face_detected = True  # default: assume OK for non-photo docs
        face_result = {
            "flagged": True,
            "face_count": -1,
            "detail": "Face check skipped — document type does not carry a photo",
        }
        if is_photo_doc:
            face_result = self._check_face_presence(img_bgr)
            face_detected = face_result.get("face_count", 0) > 0
            if not face_result["flagged"]:
                fraud_flags.append("NO_FACE_DETECTED")
        else:
            face_detected = True  # Not applicable — don't penalise
        signals["face_presence"] = face_result

        # Compute overall risk
        risk_score = self._compute_risk_score(fraud_flags)
        risk_level = self._risk_level(risk_score)

        logger.info(
            f"Fraud detection complete: flags={fraud_flags}, "
            f"risk_score={risk_score:.2f}, risk_level={risk_level}"
        )

        return FraudDetectionResponse(
            request_id=str(uuid.uuid4()),
            fraud_risk=risk_level,
            fraud_score=round(risk_score, 4),
            signals=signals,
            status="SUCCESS",
            fraud_flags=fraud_flags,
            face_detected=face_detected,
            success=True
        )

    # ------------------------------------------------------------------
    # Individual checks (3 active signals)
    # ------------------------------------------------------------------

    def _check_blur(self, gray: np.ndarray) -> dict:
        """Laplacian variance. Low variance = blurry image."""
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        flagged = lap_var < BLUR_LAPLACIAN_THRESHOLD
        return {
            "flagged": flagged,
            "laplacian_variance": round(lap_var, 4),
            "threshold": BLUR_LAPLACIAN_THRESHOLD,
            "detail": f"{'BLURRY' if flagged else 'SHARP'} (variance={lap_var:.2f})",
        }

    def _check_overexposure(self, gray: np.ndarray) -> dict:
        """Detects severely overexposed images where text is washed out."""
        total_pixels = gray.size
        overexposed = int(np.sum(gray > OVEREXPOSURE_THRESHOLD))
        fraction = overexposed / total_pixels
        flagged = fraction > OVEREXPOSURE_FRACTION
        return {
            "flagged": flagged,
            "overexposed_fraction": round(fraction, 4),
            "threshold_fraction": OVEREXPOSURE_FRACTION,
            "detail": f"{fraction*100:.1f}% pixels > {OVEREXPOSURE_THRESHOLD}",
        }

    def _check_face_presence(self, bgr: np.ndarray) -> dict:
        """
        Detect faces using a multi-cascade, multi-preset waterfall strategy.
        Tries several Haar cascade models and sensitivity settings in priority
        order, stopping as soon as a face is found.  Both the plain gray image
        and its histogram-equalised version are tested so that over/under-
        exposed document photos are handled robustly.
        Flagged = True means face IS present (not a fraud flag by itself).
        """
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        gray_eq = cv2.equalizeHist(gray)

        # Detection presets: (scaleFactor, minNeighbors, minSize, use_equalized)
        # Ordered from conservative → sensitive so we reduce false positives
        presets = [
            (1.1,  4, (24, 24), True),
            (1.1,  4, (24, 24), False),
            (1.05, 3, (20, 20), True),
            (1.05, 3, (20, 20), False),
            (1.05, 2, (20, 20), True),
        ]

        face_count = 0
        face_boxes = []
        cascade_used = "none"

        for cascade_path in FACE_CASCADE_PATHS:
            cascade = cv2.CascadeClassifier(cascade_path)
            if cascade.empty():
                continue
            for scale, neighbors, size, use_eq in presets:
                target = gray_eq if use_eq else gray
                faces = cascade.detectMultiScale(
                    target,
                    scaleFactor=scale,
                    minNeighbors=neighbors,
                    minSize=size,
                )
                if faces is not None and len(faces) > 0:
                    face_count = len(faces)
                    face_boxes = faces.tolist()
                    cascade_used = cascade_path.split("\\")[-1].split("/")[-1]
                    break
            if face_count > 0:
                break

        return {
            "flagged": face_count > 0,  # True = face found (good)
            "face_count": face_count,
            "face_boxes": face_boxes,
            "cascade_used": cascade_used,
            "detail": f"{face_count} face(s) detected" + (f" via {cascade_used}" if face_count > 0 else ""),
        }

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    def _compute_risk_score(self, fraud_flags: list) -> float:
        """
        Weighted risk score [0, 1] based on 3 active signals.

        Signal weights (chosen so a single quality issue = LOW risk):
          BLUR            0.25  — image too blurry to read reliably
          OVER_EXPOSURE   0.25  — extreme brightness washing out text
          NO_FACE_DETECTED 0.50 — photo-bearing doc has no detected face

        Score bands:
          < 0.35 → LOW      (one minor quality issue)
          < 0.70 → MEDIUM   (blurry + overexposed, or face not found on Passport/DL)
          ≥ 0.70 → HIGH     (face missing + another quality issue)
        """
        weights = {
            "BLUR":             0.25,
            "OVER_EXPOSURE":    0.25,
            "NO_FACE_DETECTED": 0.50,
        }
        score = sum(weights.get(flag, 0.0) for flag in fraud_flags)
        return min(score, 1.0)

    def _risk_level(self, score: float) -> str:
        if score < 0.35:
            return "LOW"
        if score < 0.70:
            return "MEDIUM"
        return "HIGH"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _decode_image(self, b64_str: str) -> np.ndarray:
        """Decode base64 image string (with or without data URI prefix) to BGR ndarray."""
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("cv2.imdecode returned None — unsupported image format")
        return img
