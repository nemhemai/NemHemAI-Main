# app/core/ocr_config.py
import pytesseract
import os
from pathlib import Path


class OCRConfig:
    """
    Centralized configuration for Tesseract OCR.
    Ensures pytesseract always knows where the binary and language data exist.
    """

    # Path to the Tesseract executable
    TESSERACT_CMD = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

    # Path to trained language data (dynamic project-level tessdata folder)
    TESSDATA_PREFIX = str(Path(__file__).resolve().parents[2] / "data" / "tessdata")

    # Languages used for OCR (Indian multilingual support)
    # Corrected 'pun' to 'pan' for Punjabi language pack alignment
    OCR_LANGUAGES = "eng+hin+mar+guj+ben+tam+tel+kan+mal+ori+pan+asm"

    @staticmethod
    def configure():
        """
        Configure pytesseract environment once.
        """
        pytesseract.pytesseract.tesseract_cmd = OCRConfig.TESSERACT_CMD
        os.environ["TESSDATA_PREFIX"] = OCRConfig.TESSDATA_PREFIX