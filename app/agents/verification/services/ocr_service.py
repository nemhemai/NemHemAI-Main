import uuid
import time
import cv2
from rapidocr_onnxruntime import RapidOCR

from app.agents.verification.core.logger import logger
from app.agents.verification.core.exceptions import AppException

# =========================================
# OCR SERVICE
# =========================================

class OCRService:

    # Initialize the engine once for maximum speed (Singleton pattern)
    _engine = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            # Loads PaddleOCR models running strictly on ONNX (CPU optimized)
            cls._engine = RapidOCR()
        return cls._engine

    @staticmethod
    def extract_text(processed_pages: list):

        start_time = time.time()

        logger.info("OCR extraction started (RapidOCR)")

        all_lines = []
        full_text = ""
        
        # Fetch the initialized ONNX engine
        engine = OCRService.get_engine()

        for page in processed_pages:

            image_path = page.get("processed_path") or page.get("normalized_path")

            try:
                # =====================================
                # IMAGE INFO
                # =====================================

                img = cv2.imread(image_path)

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

                logger.info("Before OCR", image_path=image_path)

                # =====================================
                # OCR WITH RAPID OCR (Paddle ONNX)
                # =====================================
                
                # result is a list of lines, elapse is processing time
                result, elapse = engine(img)

                if result:
                    for line_data in result:
                        # line_data format: [bounding_box, text, confidence]
                        text = line_data[1].strip()
                        conf = float(line_data[2])
                        
                        if text:
                            all_lines.append({
                                "text": text,
                                "confidence": conf
                            })
                            full_text += text + "\n"

                logger.info("After OCR", image_path=image_path)

            except Exception as e:
                print("\nOCR ERROR:\n", str(e))
                raise AppException(
                    message=str(e),
                    error_code="OCR_FAILED",
                    status_code=500
                )

        total_time = time.time() - start_time

        logger.info(
            "OCR extraction complete",
            total_lines=len(all_lines),
            time_taken=total_time
        )

        return {
            "request_id": str(uuid.uuid4()),
            "lines": all_lines,
            "full_text": full_text.strip()
        }