import re
import logging
from app.agents.verification.core.logger import get_logger
from app.agents.verification.core.constants import (
    DOCUMENT_TYPE_AADHAAR,
    DOCUMENT_TYPE_PAN,
    DOCUMENT_TYPE_PASSPORT,
    DOCUMENT_TYPE_DRIVING_LICENSE,
    DOCUMENT_TYPE_INCOME_CERTIFICATE,
    DOCUMENT_TYPE_CASTE_CERTIFICATE,
    DOCUMENT_TYPE_BANK_PASSBOOK,
    DOCUMENT_TYPE_LAND_RECORDS,
    DOCUMENT_TYPE_RATION_CARD,
    DOCUMENT_TYPE_DOMICILE_CERTIFICATE,
    DOCUMENT_TYPE_VENDING_CERTIFICATE,
    DOCUMENT_TYPE_NO_PUCCA_HOUSE_DECLARATION,
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
            DOCUMENT_TYPE_DRIVING_LICENSE: 0,
            DOCUMENT_TYPE_INCOME_CERTIFICATE: 0,
            DOCUMENT_TYPE_CASTE_CERTIFICATE: 0,
            DOCUMENT_TYPE_BANK_PASSBOOK: 0,
            DOCUMENT_TYPE_LAND_RECORDS: 0,
            DOCUMENT_TYPE_RATION_CARD: 0,
            DOCUMENT_TYPE_DOMICILE_CERTIFICATE: 0,
            DOCUMENT_TYPE_VENDING_CERTIFICATE: 0,
            DOCUMENT_TYPE_NO_PUCCA_HOUSE_DECLARATION: 0,
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
        if re.search(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 10
        elif re.search(r"\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{6}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 8
        elif re.search(r"\b[A-Z]{2}\d{13,15}\b", text_upper):
            scores[DOCUMENT_TYPE_DRIVING_LICENSE] += 6

        # --- Income Certificate Indicators ---
        income_high = ["INCOME CERTIFICATE", "ANNUAL INCOME", "SALARY CERTIFICATE"]
        income_med = ["ANNUAL FINANCIAL", "YEARLY INCOME", "INCOME LIMIT", "TEHSILDAR", "TAHSILDAR", "ECONOMIC ASSESSMENT", "TAHSILOFFICE", "SETU", "SUVIDHA", "KENDRA"]
        for kw in income_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_INCOME_CERTIFICATE] += 5
        for kw in income_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_INCOME_CERTIFICATE] += 2

        # --- Caste Certificate Indicators ---
        caste_high = ["CASTE CERTIFICATE", "CATEGORY CERTIFICATE", "SCHEDULED CASTE", "SCHEDULED TRIBE", "OBC CERTIFICATE", "COMMUNITY CERTIFICATE"]
        caste_med = ["BACKWARD CLASS", "SOCIAL STATUS", "SEBC", "SOCIALLY AND EDUCATIONALLY"]
        for kw in caste_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_CASTE_CERTIFICATE] += 5
        for kw in caste_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_CASTE_CERTIFICATE] += 2

        # --- Bank Passbook Indicators ---
        bank_high = ["BANK PASSBOOK", "PASSBOOK", "CANCELLED CHEQUE", "IFSC CODE", "ACCOUNT NUMBER", "IFSC", "RTGS/NEFT", "OR ORDER"]
        bank_med = ["ACCOUNT HOLDER", "SAVINGS ACCOUNT", "CHEQUE", "CANCELED CHEQUE", "MICR CODE", "BRANCH NAME", "RUPEES", "SAVINGS A/C", "A/C NO", "A/C.NO", "AC.NO", "BANK OF"]
        for kw in bank_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_BANK_PASSBOOK] += 5
        for kw in bank_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_BANK_PASSBOOK] += 2

        # --- Land Records Indicators ---
        land_high = ["LAND RECORDS", "KHASRA", "KHATAUNI", "RECORD OF RIGHTS", "PATTA"]
        land_med = ["SURVEY NUMBER", "LAND AREA", "OWNERSHIP PROOF", "ACRES", "HECTARES", "MUTATION ENTRY"]
        for kw in land_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_LAND_RECORDS] += 5
        for kw in land_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_LAND_RECORDS] += 2

        # --- Ration Card Indicators ---
        ration_high = ["RATION CARD", "RATION CARD NUMBER"]
        ration_med = ["HEAD OF FAMILY", "FAMILY MEMBERS", "BPL", "APL", "HOUSEHOLD VERIFICATION", "FOOD SECURITY"]
        for kw in ration_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_RATION_CARD] += 5
        for kw in ration_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_RATION_CARD] += 2

        # --- Domicile Certificate Indicators ---
        domicile_high = ["DOMICILE CERTIFICATE", "DOMICILE", "AGE, NATIONALITY", "BONAFIDE RESIDENT", "RESIDENCE CERTIFICATE"]
        domicile_med = ["RESIDENT CERTIFICATE", "DOMICILE OF", "REVENUE DEPARTMENT", "PERMANENT RESIDENCE"]
        for kw in domicile_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_DOMICILE_CERTIFICATE] += 5
        for kw in domicile_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_DOMICILE_CERTIFICATE] += 2

        # --- Vending Certificate Indicators ---
        vending_high = ["VENDING CERTIFICATE", "STREET VENDOR", "STREET VENDING", "ULB-TVC", "TOWN VENDING"]
        vending_med = ["RECOMMENDATION LETTER", "VENDOR ID", "VENDING LICENSE", "MUNICIPAL CORPORATION"]
        for kw in vending_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_VENDING_CERTIFICATE] += 5
        for kw in vending_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_VENDING_CERTIFICATE] += 2

        # --- No Pucca House Declaration Indicators ---
        pucca_high = ["NO PUCCA HOUSE", "PUCCA HOUSE", "AFFIDAVIT", "DECLARATION", "NOTARY", "STAMP PAPER", "DEPONENT", "DO NOT OWN", "KUTCHA"]
        pucca_med = ["OATH", "SOLEMNLY AFFIRM", "I HEREBY DECLARE"]
        for kw in pucca_high:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_NO_PUCCA_HOUSE_DECLARATION] += 5
        for kw in pucca_med:
            if kw in text_upper:
                scores[DOCUMENT_TYPE_NO_PUCCA_HOUSE_DECLARATION] += 2

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

        score_details = ", ".join([f"{k}={v}" for k, v in scores.items() if v > 0])
        logger.info(
            f"Classification results: {score_details}. Winner: {best_doc_type}"
        )
        return best_doc_type
