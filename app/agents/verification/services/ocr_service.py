import os
import uuid
import time
import cv2

# Disable PaddlePaddle PIR executor API to prevent Windows executor crashes
os.environ["FLAGS_use_pir_api"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

# paddleocr will be imported lazily

from app.agents.verification.core.logger import logger
from app.agents.verification.core.exceptions import AppException


# =========================================
# INITIALIZE OCR ENGINE
# =========================================

# OCR engine is initialised lazily on first use to avoid blocking server startup
_ocr_engine = None


def get_ocr_engine() -> "PaddleOCR":
    """Return a shared PaddleOCR instance, creating it on first call."""
    global _ocr_engine
    if _ocr_engine is None:
        logger.info("Initialising PaddleOCR engine (first use)...")
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(
            use_angle_cls=False,
            lang="en",
            enable_mkldnn=False,
            ocr_version="PP-OCRv4",
        )
        logger.info("PaddleOCR engine ready.")
    return _ocr_engine


# =========================================
# OCR SERVICE
# =========================================

class OCRService:

    @staticmethod
    def extract_text(
        processed_pages: list
    ):

        start_time = time.time()

        logger.info(
            "OCR extraction started"
        )

        all_lines = []

        full_text = ""

        for page in processed_pages:

            image_path = (
                page.get("processed_path") or page.get("normalized_path")
            )

            try:

                # =====================================
                # IMAGE INFO
                # =====================================

                img = cv2.imread(
                    image_path
                )

                if img is None:

                    raise AppException(
                        message="Unable to read processed image",
                        error_code="INVALID_IMAGE",
                        status_code=400
                    )

                logger.info(
                    "Image dimensions",
                    width=img.shape[1],
                    height=img.shape[0]
                )

                logger.info(
                    "Before OCR",
                    image_path=image_path
                )

                # =====================================
                # OCR
                # =====================================

                results = get_ocr_engine().ocr(
                    image_path
                )

                logger.info(
                    "After OCR",
                    image_path=image_path
                )

            except Exception as e:

                print(
                    "\nOCR ERROR:\n",
                    str(e)
                )

                raise AppException(
                    message=str(e),
                    error_code="OCR_FAILED",
                    status_code=500
                )

            if not results:

                continue

            # =====================================
            # PARSE OCR RESULTS
            # =====================================

            if isinstance(results, list):

                for page_result in results:

                    if not page_result:
                        continue

                    # Support PaddleX / modern PaddleOCR format (dictionary)
                    if isinstance(page_result, dict) and "rec_texts" in page_result:
                        texts = page_result["rec_texts"]
                        scores = page_result.get("rec_scores")
                        if scores is None:
                            scores = [1.0] * len(texts)
                        rec_boxes = page_result.get("rec_boxes")
                        # rec_boxes may be a numpy array — avoid truthiness check on arrays
                        bboxes = (
                            list(rec_boxes) if rec_boxes is not None else [None] * len(texts)
                        )
                        for t, s, b in zip(texts, scores, bboxes):
                            if float(s) < 0.50:
                                continue  # skip low-confidence tokens
                            y_pos = float(b[1]) if (b is not None and len(b) >= 2) else 0
                            all_lines.append({
                                "text": t,
                                "confidence": float(s),
                                "_y": y_pos,
                            })
                    # Support legacy format (list of lines with bounding boxes)
                    else:
                        for line in page_result:
                            try:
                                text = line[1][0]
                                confidence = float(line[1][1])
                                if confidence < 0.50:
                                    continue  # skip low-confidence tokens
                                # bbox format: [[x0,y0],[x1,y1],[x2,y2],[x3,y3]]
                                bbox = line[0] if line[0] else []
                                y_pos = bbox[0][1] if (bbox and len(bbox) > 0) else 0
                                all_lines.append({
                                    "text": text,
                                    "confidence": confidence,
                                    "_y": y_pos,
                                })
                            except Exception:
                                continue

            else:

                logger.info(
                    "Unexpected OCR result type",
                    result_type=str(
                        type(results)
                    )
                )

        # =====================================
        # SPATIAL SORT: re-order lines top-to-bottom
        # PaddleOCR does not guarantee reading order across the whole page.
        # Sort by the stored Y coordinate so field extractors see lines
        # in natural document order (top → bottom).
        # =====================================
        all_lines.sort(key=lambda ln: ln.get("_y", 0))

        # Strip internal sorting key and build full_text from sorted lines
        for ln in all_lines:
            ln.pop("_y", None)  # remove internal sort key
            full_text += ln["text"] + "\n"

        total_time = (
            time.time() - start_time
        )

        logger.info(
            "OCR extraction complete",
            total_lines=len(
                all_lines
            ),
            time_taken=total_time
        )

        return {

            "request_id": str(
                uuid.uuid4()
            ),

            "total_pages": len(
                processed_pages
            ),

            "extracted_text": (
                full_text.strip()
            ),

            "ocr_lines": all_lines,

            "status": "SUCCESS"
        }