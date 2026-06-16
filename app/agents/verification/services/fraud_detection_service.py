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
# Thresholds  (tune per environment)
# ---------------------------------------------------------------------------
BLUR_LAPLACIAN_THRESHOLD = 80.0       # below = blurry
OVEREXPOSURE_THRESHOLD = 220          # pixel value
OVEREXPOSURE_FRACTION = 0.15          # >15% pixels overexposed → flag
UNDEREXPOSURE_THRESHOLD = 30
UNDEREXPOSURE_FRACTION = 0.15
HOTSPOT_REGION_FRACTION = 0.005       # hotspot cluster > 0.5% of image
COMPRESSION_BLOCK_VAR_THRESHOLD = 25  # low block variance = JPEG artefacts
# Multiple cascades tried in priority order
FACE_CASCADE_PATHS = [
    cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml",
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
    cv2.data.haarcascades + "haarcascade_frontalface_alt.xml",
]

# Border crop detection
CROP_BORDER_DARK_FRACTION = 0.15      # >15% of border rows/cols near-black → crop
CROP_BORDER_BRIGHT_FRACTION = 0.90   # >90% of border rows/cols saturated → crop


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
    def detect(image_path: str) -> dict:
        service = FraudDetectionService()
        request = FraudDetectionRequest(image_path=image_path)
        res = service.detect_request(request)
        return res.model_dump()

    def detect_request(self, request: FraudDetectionRequest) -> FraudDetectionResponse:
        logger.info(f"Starting fraud detection on path: {request.image_path}")

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

        # 1. Blur
        blur_result = self._check_blur(img_gray)
        signals["blur"] = blur_result
        if blur_result["flagged"]:
            fraud_flags.append("BLUR")

        # 2. Over-exposure
        over_result = self._check_overexposure(img_gray)
        signals["overexposure"] = over_result
        if over_result["flagged"]:
            fraud_flags.append("OVER_EXPOSURE")

        # 3. Under-exposure
        under_result = self._check_underexposure(img_gray)
        signals["underexposure"] = under_result
        if under_result["flagged"]:
            fraud_flags.append("UNDER_EXPOSURE")

        # 4. Flash hotspot
        hotspot_result = self._check_flash_hotspot(img_bgr)
        signals["flash_hotspot"] = hotspot_result
        if hotspot_result["flagged"]:
            fraud_flags.append("FLASH_HOTSPOT")

        # 5. JPEG compression artefacts
        compression_result = self._check_compression_artifacts(img_gray)
        signals["compression_artifacts"] = compression_result
        if compression_result["flagged"]:
            fraud_flags.append("COMPRESSION_ARTIFACTS")

        # 6. Crop / border tamper
        crop_result = self._check_crop(img_gray)
        signals["crop_tamper"] = crop_result
        if crop_result["flagged"]:
            fraud_flags.append("CROP_TAMPER")

        # 7. Face presence
        face_result = self._check_face_presence(img_bgr)
        signals["face_presence"] = face_result
        if not face_result["flagged"]:
            fraud_flags.append("NO_FACE_DETECTED")

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
            face_detected=face_result.get("face_count", 0) > 0,
            success=True
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_blur(self, gray: np.ndarray) -> dict:
        """Laplacian variance. Low variance = blurry."""
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        flagged = lap_var < BLUR_LAPLACIAN_THRESHOLD
        return {
            "flagged": flagged,
            "laplacian_variance": round(lap_var, 4),
            "threshold": BLUR_LAPLACIAN_THRESHOLD,
            "detail": f"{'BLURRY' if flagged else 'SHARP'} (variance={lap_var:.2f})",
        }

    def _check_overexposure(self, gray: np.ndarray) -> dict:
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

    def _check_underexposure(self, gray: np.ndarray) -> dict:
        total_pixels = gray.size
        underexposed = int(np.sum(gray < UNDEREXPOSURE_THRESHOLD))
        fraction = underexposed / total_pixels
        flagged = fraction > UNDEREXPOSURE_FRACTION
        return {
            "flagged": flagged,
            "underexposed_fraction": round(fraction, 4),
            "threshold_fraction": UNDEREXPOSURE_FRACTION,
            "detail": f"{fraction*100:.1f}% pixels < {UNDEREXPOSURE_THRESHOLD}",
        }

    def _check_flash_hotspot(self, bgr: np.ndarray) -> dict:
        """
        Detect intense localised bright regions (flash hotspot) using
        HSV value channel + connected components.
        """
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # Threshold: pixels with value > 250 (near-white saturation)
        _, bright_mask = cv2.threshold(v_channel, 250, 255, cv2.THRESH_BINARY)

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            bright_mask, connectivity=8
        )
        total_pixels = bgr.shape[0] * bgr.shape[1]

        # Any component larger than threshold → hotspot
        hotspot_found = False
        max_component_fraction = 0.0
        for i in range(1, num_labels):  # skip background (0)
            area = stats[i, cv2.CC_STAT_AREA]
            fraction = area / total_pixels
            max_component_fraction = max(max_component_fraction, fraction)
            if fraction > HOTSPOT_REGION_FRACTION:
                hotspot_found = True

        return {
            "flagged": hotspot_found,
            "max_bright_region_fraction": round(max_component_fraction, 4),
            "threshold_fraction": HOTSPOT_REGION_FRACTION,
            "detail": f"Flash hotspot: {'DETECTED' if hotspot_found else 'NONE'}",
        }

    def _check_compression_artifacts(self, gray: np.ndarray) -> dict:
        """
        Detect JPEG block artefacts by computing variance within 8×8 blocks.
        Low intra-block variance + high inter-block discontinuity → heavy compression.
        """
        h, w = gray.shape
        # Crop to nearest multiple of 8
        h8 = (h // 8) * 8
        w8 = (w // 8) * 8
        gray8 = gray[:h8, :w8].astype(np.float32)

        blocks = gray8.reshape(h8 // 8, 8, w8 // 8, 8)
        # Variance per 8×8 block
        block_vars = blocks.var(axis=(1, 3))
        mean_block_var = float(block_vars.mean())

        flagged = mean_block_var < COMPRESSION_BLOCK_VAR_THRESHOLD
        return {
            "flagged": flagged,
            "mean_block_variance": round(mean_block_var, 4),
            "threshold": COMPRESSION_BLOCK_VAR_THRESHOLD,
            "detail": (
                f"Mean 8×8 block variance {mean_block_var:.2f}: "
                f"{'HEAVY COMPRESSION' if flagged else 'OK'}"
            ),
        }

    def _check_crop(self, gray: np.ndarray) -> dict:
        """
        Detect unnatural border crops by checking if border rows/columns
        are anomalously dark (black border) or saturated (white border).
        """
        h, w = gray.shape
        border_size = max(3, int(min(h, w) * 0.02))

        borders = np.concatenate([
            gray[:border_size, :].flatten(),   # top
            gray[-border_size:, :].flatten(),  # bottom
            gray[:, :border_size].flatten(),   # left
            gray[:, -border_size:].flatten(),  # right
        ])

        dark_fraction = float(np.sum(borders < 20) / len(borders))
        bright_fraction = float(np.sum(borders > 235) / len(borders))

        flagged = dark_fraction > CROP_BORDER_DARK_FRACTION or bright_fraction > CROP_BORDER_BRIGHT_FRACTION
        return {
            "flagged": flagged,
            "border_dark_fraction": round(dark_fraction, 4),
            "border_bright_fraction": round(bright_fraction, 4),
            "detail": (
                f"Border dark={dark_fraction*100:.1f}%, bright={bright_fraction*100:.1f}%: "
                f"{'POSSIBLE CROP' if flagged else 'OK'}"
            ),
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
        Weighted risk score [0, 1].
        Weights represent how strongly each flag indicates fraud/tamper.
        """
        weights = {
            "BLUR": 0.15,
            "OVER_EXPOSURE": 0.15,
            "UNDER_EXPOSURE": 0.15,
            "FLASH_HOTSPOT": 0.20,
            "COMPRESSION_ARTIFACTS": 0.10,
            "CROP_TAMPER": 0.25,
            "NO_FACE_DETECTED": 0.30,
        }
        score = sum(weights.get(flag, 0.10) for flag in fraud_flags)
        return min(score, 1.0)

    def _risk_level(self, score: float) -> str:
        if score < 0.50:
            return "LOW"
        if score < 0.80:
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
