import re
import logging
from app.core.logger import get_logger
from app.core.constants import (
    DOCUMENT_TYPE_AADHAAR,
    DOCUMENT_TYPE_PAN,
    DOCUMENT_TYPE_PASSPORT,
    DOCUMENT_TYPE_DRIVING_LICENSE,
    DOCUMENT_TYPE_UNKNOWN
)

logger = get_logger(__name__)

class ClassificationService:
    """
    Classifies a document based on raw OCR extracted text.
    """

    @staticmethod
    def classify(extracted_text: str) -> str:
        logger.info("Starting document classification based on text keywords")
        
        if not extracted_text:
            logger.warning("Extracted text is empty. Classifying as UNKNOWN.")
            return DOCUMENT_TYPE_UNKNOWN

        text_upper = extracted_text.upper()

        # Score mapping
        scores = {
            DOCUMENT_TYPE_AADHAAR: 0,
            DOCUMENT_TYPE_PAN: 0,
            DOCUMENT_TYPE_PASSPORT: 0,
            DOCUMENT_TYPE_DRIVING_LICENSE: 0
        }

        # --- Aadhaar Indicators ---
        aadhaar_keywords = [
            "UNIQUE IDENTIFICATION", "AADHAAR", "GOVERNMENT OF INDIA",
            "MALE", "FEMALE", "TRANSGENDER", "ENROLLMENT", "VID", "HELP",
            "MINISTRY OF HOME", "IDENTIFICATION AUTHORITY", "CARD"
        ]
        for kw in aadhaar_keywords:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_AADHAAR] += 1
        
        # 12 digit pattern (often spaced XXXX XXXX XXXX)
        if re.search(r"\b\d{4}\s\d{4}\s\d{4}\b", extracted_text):
            scores[DOCUMENT_TYPE_AADHAAR] += 5
        elif re.search(r"\b\d{12}\b", extracted_text):
            scores[DOCUMENT_TYPE_AADHAAR] += 3

        # --- PAN Indicators ---
        pan_keywords = [
            "INCOME TAX DEPARTMENT", "INCOME TAX", "TAX", "DEPARTMENT",
            "PERMANENT ACCOUNT NUMBER", "GOVT. OF INDIA", "GOVT OF INDIA",
            "CARD", "FATHER'S NAME", "FATHERS NAME", "SIGNATURE", "ACCOUNT"
        ]
        for kw in pan_keywords:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_PAN] += 1
        
        # PAN ID regex [A-Z]{5}[0-9]{4}[A-Z]
        if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", text_upper):
            scores[DOCUMENT_TYPE_PAN] += 8

        # --- Passport Indicators ---
        passport_keywords = [
            "REPUBLIC OF INDIA", "PASSPORT", "SURNAME", "GIVEN NAME",
            "NATIONALITY", "PLACE OF BIRTH", "PLACE OF ISSUE",
            "DATE OF ISSUE", "DATE OF EXPIRY", "EXPIRY DATE", "SEX"
        ]
        for kw in passport_keywords:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_PASSPORT] += 1

        # Passport number pattern (India: letter + 7 digits)
        if re.search(r"\b[A-Z]\d{7}\b", text_upper):
            scores[DOCUMENT_TYPE_PASSPORT] += 6

        # MRZ lines (44 characters of capitals/digits/<)
        mrz_lines = re.findall(r"[A-Z0-9<]{44}", text_upper)
        if len(mrz_lines) >= 2:
            scores[DOCUMENT_TYPE_PASSPORT] += 10
        elif len(mrz_lines) == 1:
            scores[DOCUMENT_TYPE_PASSPORT] += 4

        # --- Driving License Indicators ---
        dl_keywords = [
            "DRIVING LICENCE", "DRIVING LICENSE", "DRIVER'S LICENCE", "DRIVER LICENSE",
            "MOTOR VEHICLES", "TRANSPORT DEPARTMENT", "VEHICLE CLASS",
            "COV", "LMV", "HMV", "MCWG", "MCWOG", "TRANSPORT",
            "LICENSE TO DRIVE", "LICENCE NO", "LICENSE NO", "DL NO",
            "VALID TILL", "BLOOD GROUP", "ISSUED BY", "RTO"
        ]
        for kw in dl_keywords:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 1

        # Indian DL number format: STATE_CODE + YY + NUMBER (e.g. MH-12-20230012345)
        # Various formats: MH0120230012345, MH-01-2023-0012345, DL-0420110149646
        if re.search(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 10
        elif re.search(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{6}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 8
        elif re.search(r"\b[A-Z]{2}\d{13,15}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 6

        # Determine highest scoring document type
        max_score = 0
        best_doc_type = DOCUMENT_TYPE_UNKNOWN
        
        for doc_type, score in scores.items():
            if score > max_score:
                max_score = score
                best_doc_type = doc_type

        # Minimum score threshold to classify
        if max_score < 2:
            logger.info(f"Scores too low ({scores}). Document classified as UNKNOWN.")
            return DOCUMENT_TYPE_UNKNOWN

        logger.info(
            f"Classification results: Aadhaar={scores[DOCUMENT_TYPE_AADHAAR]}, "
            f"PAN={scores[DOCUMENT_TYPE_PAN]}, Passport={scores[DOCUMENT_TYPE_PASSPORT]}. "
            f"Winner: {best_doc_type}"
        )
        return best_doc_type
