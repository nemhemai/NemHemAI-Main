import os
import uuid
import time
import cv2

# Disable PaddlePaddle PIR executor API to prevent Windows executor crashes
os.environ["FLAGS_use_pir_api"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from paddleocr import PaddleOCR

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
                        scores = page_result.get("rec_scores") or [1.0] * len(texts)
                        for t, s in zip(texts, scores):
                            all_lines.append({
                                "text": t,
                                "confidence": float(s)
                            })
                            full_text += t + "\n"
                    # Support legacy format (list of lines)
                    else:
                        for line in page_result:
                            try:
                                text = line[1][0]
                                confidence = float(line[1][1])
                                all_lines.append({
                                    "text": text,
                                    "confidence": confidence
                                })
                                full_text += text + "\n"
                            except Exception:
                                continue

            else:

                logger.info(
                    "Unexpected OCR result type",
                    result_type=str(
                        type(results)
                    )
                )

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