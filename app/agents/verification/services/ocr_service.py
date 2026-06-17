import uuid
import time
import cv2
import pytesseract
from pytesseract import Output

from app.agents.verification.core.logger import logger
from app.agents.verification.core.exceptions import AppException

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
            "OCR extraction started (PyTesseract)"
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
                # OCR WITH PYTESSERACT
                # =====================================

                data = pytesseract.image_to_data(img, output_type=Output.DICT)
                
                # Reconstruct lines from words
                current_line = []
                current_line_num = -1
                current_conf = []

                n_boxes = len(data['level'])
                for i in range(n_boxes):
                    if data['level'][i] == 5: # Word level
                        text = data['text'][i].strip()
                        conf = float(data['conf'][i])
                        line_num = data['line_num'][i]
                        block_num = data['block_num'][i]
                        par_num = data['par_num'][i]
                        
                        # Use a composite key for line identification
                        line_id = f"{block_num}_{par_num}_{line_num}"

                        if text and conf > -1:
                            if line_id != current_line_num and current_line:
                                # Save previous line
                                line_text = " ".join(current_line)
                                avg_conf = sum(current_conf) / len(current_conf) / 100.0
                                all_lines.append({
                                    "text": line_text,
                                    "confidence": avg_conf
                                })
                                full_text += line_text + "\n"
                                
                                # Reset for new line
                                current_line = []
                                current_conf = []
                            
                            current_line_num = line_id
                            current_line.append(text)
                            current_conf.append(conf)

                # Add the last line if exists
                if current_line:
                    line_text = " ".join(current_line)
                    avg_conf = sum(current_conf) / len(current_conf) / 100.0
                    all_lines.append({
                        "text": line_text,
                        "confidence": avg_conf
                    })
                    full_text += line_text + "\n"

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