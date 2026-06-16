import re
import logging
from datetime import datetime
from typing import Optional

from app.agents.verification.schemas.schemas import VerificationRequest, VerificationResponse
from app.agents.verification.core.constants import DOCUMENT_TYPE_AADHAAR, DOCUMENT_TYPE_PAN, DOCUMENT_TYPE_PASSPORT, DOCUMENT_TYPE_DRIVING_LICENSE
from app.agents.verification.core.exceptions import VerificationError
from app.agents.verification.core.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Verhoeff checksum tables
# ---------------------------------------------------------------------------

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


import uuid

class VerificationService:
    """
    Validates extracted document fields against format rules and checksums.
    Supports Aadhaar, PAN, and Passport.
    """

    @staticmethod
    def verify(document_type: str, extracted_fields: dict) -> dict:
        service = VerificationService()
        request = VerificationRequest(
            document_type=document_type,
            extracted_fields=extracted_fields
        )
        res = service.verify_request(request)
        return res.model_dump()

    def verify_request(self, request: VerificationRequest) -> VerificationResponse:
        doc_type = (request.document_type or "").upper()
        fields = request.extracted_fields or {}
        logger.info(f"Starting verification for doc_type={doc_type}")

        checks = {}
        passed = []
        failed = []

        try:
            if doc_type == DOCUMENT_TYPE_AADHAAR:
                checks = self._verify_aadhaar(fields)
            elif doc_type == DOCUMENT_TYPE_PAN:
                checks = self._verify_pan(fields)
            elif doc_type == DOCUMENT_TYPE_PASSPORT:
                checks = self._verify_passport(fields)
            elif doc_type == DOCUMENT_TYPE_DRIVING_LICENSE:
                checks = self._verify_driving_license(fields)
            else:
                logger.warning(f"Unknown doc_type={doc_type}, running common checks only")
                checks = self._verify_common(fields)

            for check_name, result in checks.items():
                if result["passed"]:
                    passed.append(check_name)
                else:
                    failed.append(check_name)

            overall = len(failed) == 0
            confidence = round(len(passed) / max(len(checks), 1), 4)

            logger.info(
                f"Verification done: passed={passed}, failed={failed}, overall={overall}"
            )

            return VerificationResponse(
                request_id=str(uuid.uuid4()),
                document_type=doc_type,
                verified=overall,
                verification_details=checks,
                status="SUCCESS",
                passed_checks=passed,
                failed_checks=failed,
                success=True,
                overall_valid=overall,
                confidence=confidence,
                checks=checks
            )

        except Exception as e:
            logger.error(f"Verification error: {e}", exc_info=True)
            raise VerificationError(f"Verification failed: {str(e)}")

    # ------------------------------------------------------------------
    # Aadhaar
    # ------------------------------------------------------------------

    def _verify_aadhaar(self, fields: dict) -> dict:
        checks = {}

        # 1. Format check (12 digits)
        aadhaar_num = fields.get("aadhaar_number", "")
        format_ok = bool(re.fullmatch(r"\d{12}", aadhaar_num))
        checks["aadhaar_format"] = {
            "passed": format_ok,
            "detail": f"12-digit format: {'OK' if format_ok else 'FAIL'} (got '{aadhaar_num}')",
        }

        # 2. Verhoeff checksum
        if format_ok:
            verhoeff_ok = self._verhoeff_validate(aadhaar_num)
            checks["aadhaar_verhoeff_checksum"] = {
                "passed": verhoeff_ok,
                "detail": f"Verhoeff checksum: {'VALID' if verhoeff_ok else 'INVALID'}",
            }
        else:
            checks["aadhaar_verhoeff_checksum"] = {
                "passed": False,
                "detail": "Skipped — format check failed",
            }

        # 3. First digit must not be 0 or 1
        if format_ok:
            first_digit_ok = aadhaar_num[0] not in ("0", "1")
            checks["aadhaar_first_digit"] = {
                "passed": first_digit_ok,
                "detail": f"First digit '{aadhaar_num[0]}': {'OK' if first_digit_ok else 'FAIL (cannot be 0 or 1)'}",
            }

        # 4. DOB
        checks.update(self._verify_common(fields))

        return checks

    # ------------------------------------------------------------------
    # PAN
    # ------------------------------------------------------------------

    def _verify_pan(self, fields: dict) -> dict:
        checks = {}

        pan_num = fields.get("pan_number", "")
        pan_pattern = r"[A-Z]{5}[0-9]{4}[A-Z]"
        format_ok = bool(re.fullmatch(pan_pattern, pan_num))
        checks["pan_format"] = {
            "passed": format_ok,
            "detail": f"Pattern [A-Z]{{5}}[0-9]{{4}}[A-Z]: {'OK' if format_ok else 'FAIL'} (got '{pan_num}')",
        }

        # 4th character encodes entity type (P = Person)
        if format_ok:
            entity_char = pan_num[3]
            valid_entities = set("ABCFGHLJPTK")
            entity_ok = entity_char in valid_entities
            checks["pan_entity_type"] = {
                "passed": entity_ok,
                "detail": f"Entity char '{entity_char}': {'valid' if entity_ok else 'unrecognised'}",
            }

        # Name and DOB
        checks.update(self._verify_common(fields))

        # Name present
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["pan_name_present"] = {
            "passed": name_ok,
            "detail": f"Name field: {'present' if name_ok else 'missing or too short'} (got '{name}')",
        }

        return checks

    # ------------------------------------------------------------------
    # Passport
    # ------------------------------------------------------------------

    def _verify_passport(self, fields: dict) -> dict:
        checks = {}

        # Passport number format (global standard: 6-9 alphanumeric chars)
        passport_num = fields.get("passport_number") or fields.get("mrz_doc_number", "")
        # Remove any spaces or hyphens that OCR might have inserted
        passport_num_clean = re.sub(r"[\s\-]", "", passport_num)
        
        passport_fmt_ok = bool(re.fullmatch(r"[A-Z0-9]{6,9}", passport_num_clean, re.IGNORECASE))
        checks["passport_number_format"] = {
            "passed": passport_fmt_ok,
            "detail": f"Alphanumeric 6-9 chars: {'OK' if passport_fmt_ok else 'FAIL'} (got '{passport_num_clean}')",
        }

        # MRZ consistency
        mrz_line1 = fields.get("mrz_line1", "")
        mrz_line2 = fields.get("mrz_line2", "")
        mrz_present = len(mrz_line1) == 44 and len(mrz_line2) == 44
        checks["mrz_present"] = {
            "passed": mrz_present,
            "detail": f"MRZ lines (44 chars each): {'OK' if mrz_present else 'FAIL/MISSING'}",
        }

        if mrz_present:
            # MRZ check digits
            mrz_doc_check_ok = self._mrz_check_digit(mrz_line2[0:9], mrz_line2[9])
            checks["mrz_doc_number_check_digit"] = {
                "passed": mrz_doc_check_ok,
                "detail": f"MRZ doc number check digit: {'VALID' if mrz_doc_check_ok else 'INVALID'}",
            }

            mrz_dob_check_ok = self._mrz_check_digit(mrz_line2[13:19], mrz_line2[19])
            checks["mrz_dob_check_digit"] = {
                "passed": mrz_dob_check_ok,
                "detail": f"MRZ DOB check digit: {'VALID' if mrz_dob_check_ok else 'INVALID'}",
            }

            mrz_expiry_check_ok = self._mrz_check_digit(mrz_line2[21:27], mrz_line2[27])
            checks["mrz_expiry_check_digit"] = {
                "passed": mrz_expiry_check_ok,
                "detail": f"MRZ expiry check digit: {'VALID' if mrz_expiry_check_ok else 'INVALID'}",
            }

        # Expiry not in past
        expiry_str = fields.get("expiry_date") or fields.get("mrz_expiry", "")
        if expiry_str:
            expiry_ok, expiry_detail = self._check_not_expired(expiry_str)
            checks["passport_not_expired"] = {"passed": expiry_ok, "detail": expiry_detail}

        # Common (DOB, name)
        checks.update(self._verify_common(fields))

        return checks

    # ------------------------------------------------------------------
    # Driving License
    # ------------------------------------------------------------------

    def _verify_driving_license(self, fields: dict) -> dict:
        checks = {}

        # 1. DL number format: 2 uppercase letters (state) + digits (9-15 total)
        dl_num = fields.get("dl_number", "")
        dl_cleaned = re.sub(r"[\s\-]", "", dl_num).upper()
        # Indian DL: 2-letter state code + digits totalling 13-15 chars
        dl_format_ok = bool(re.fullmatch(r"[A-Z]{2}\d{11,13}", dl_cleaned))
        checks["dl_number_format"] = {
            "passed": dl_format_ok,
            "detail": f"DL format [STATE][11-13 digits]: {'OK' if dl_format_ok else 'FAIL'} (got '{dl_num}')"
        }

        # 2. State code must be a valid Indian state RTO code
        valid_state_codes = {
            "AN", "AP", "AR", "AS", "BR", "CG", "CH", "DD", "DL", "DN",
            "GA", "GJ", "HP", "HR", "JH", "JK", "KA", "KL", "LA", "LD",
            "MH", "ML", "MN", "MP", "MZ", "NL", "OD", "OR", "PB", "PY",
            "RJ", "SK", "TG", "TN", "TR", "TS", "UK", "UP", "WB"
        }
        if dl_format_ok:
            state_code = dl_cleaned[:2]
            state_ok = state_code in valid_state_codes
            checks["dl_state_code"] = {
                "passed": state_ok,
                "detail": f"State code '{state_code}': {'recognised Indian RTO state' if state_ok else 'unrecognised state code'}"
            }

        # 3. Expiry date check
        expiry_str = fields.get("expiry_date", "")
        if expiry_str:
            expiry_ok, expiry_detail = self._check_not_expired(expiry_str)
            checks["dl_not_expired"] = {"passed": expiry_ok, "detail": expiry_detail}
        else:
            checks["dl_expiry_present"] = {
                "passed": False,
                "detail": "Expiry/Valid Till date not found on document"
            }

        # 4. Vehicle class present
        vehicle_class = fields.get("vehicle_class", "").strip()
        vc_ok = len(vehicle_class) >= 2
        checks["dl_vehicle_class"] = {
            "passed": vc_ok,
            "detail": f"Vehicle class: {'present' if vc_ok else 'missing'} (got '{vehicle_class}')"
        }

        # 5. Common checks (DOB, gender)
        checks.update(self._verify_common(fields))

        return checks

    # ------------------------------------------------------------------
    # Common checks
    # ------------------------------------------------------------------

    def _verify_common(self, fields: dict) -> dict:
        checks = {}

        # DOB present and plausible
        dob = fields.get("dob", "")
        if dob:
            dob_ok, dob_detail = self._validate_dob(dob)
            checks["dob_valid"] = {"passed": dob_ok, "detail": dob_detail}
        else:
            checks["dob_present"] = {"passed": False, "detail": "DOB field missing"}

        # Gender
        gender = fields.get("gender", "")
        if gender:
            gender_ok = gender.upper() in ("MALE", "FEMALE", "TRANSGENDER", "M", "F")
            checks["gender_valid"] = {
                "passed": gender_ok,
                "detail": f"Gender '{gender}': {'OK' if gender_ok else 'UNRECOGNISED'}",
            }

        return checks

    # ------------------------------------------------------------------
    # Verhoeff algorithm
    # ------------------------------------------------------------------

    def _verhoeff_validate(self, number: str) -> bool:
        """Return True if the number passes the Verhoeff check."""
        try:
            c = 0
            for i, digit in enumerate(reversed(number)):
                c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(digit)]]
            return c == 0
        except Exception as e:
            logger.warning(f"Verhoeff validation exception: {e}")
            return False

    # ------------------------------------------------------------------
    # MRZ check digit (ISO 7064 mod-37)
    # ------------------------------------------------------------------

    def _mrz_check_digit(self, field: str, check_char: str) -> bool:
        weights = [7, 3, 1]
        char_values = {str(i): i for i in range(10)}
        char_values.update({chr(c): c - 55 for c in range(65, 91)})  # A-Z
        char_values["<"] = 0

        total = 0
        for i, ch in enumerate(field):
            total += char_values.get(ch, 0) * weights[i % 3]
        expected = total % 10
        try:
            return expected == int(check_char)
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # DOB validation
    # ------------------------------------------------------------------

    def _validate_dob(self, dob_str: str):
        import re as _re
        dob_str = dob_str.strip()
        # Normalise separators: replace space or dot or hyphen with /
        normalised = _re.sub(r"[\-\.\s]+", "/", dob_str)
        # Attempt parsing across many formats (ordered from most specific to least)
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y",
            "%d/%m/%y", "%Y/%m/%d",
            # Compact digit-only variants produced by our extractor
            "%d%m%Y", "%Y%m%d", "%d%m%y",
        ]
        candidates = list(dict.fromkeys([normalised, dob_str]))  # try normalised first
        for candidate in candidates:
            for fmt in formats:
                try:
                    dob = datetime.strptime(candidate, fmt)
                    now = datetime.now()
                    # Two-digit year fix: 2025 → 1925 if in future
                    if dob.year > now.year:
                        dob = dob.replace(year=dob.year - 100)
                    age = (now - dob).days / 365.25
                    if age < 0:
                        return False, f"DOB {dob_str} is in the future"
                    if age > 120:
                        return False, f"DOB {dob_str} implies age > 120 years"
                    return True, f"DOB {dob_str} valid, age ~{int(age)} years"
                except ValueError:
                    continue
        return False, f"DOB '{dob_str}' does not match known formats"

    def _check_not_expired(self, date_str: str):
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y", "%m/%y", "%m/%Y"]
        for fmt in formats:
            try:
                exp = datetime.strptime(date_str.strip(), fmt)
                if exp < datetime.now():
                    return False, f"Document expired on {date_str}"
                return True, f"Document valid until {date_str}"
            except ValueError:
                continue
        return True, f"Could not parse expiry date '{date_str}', assuming valid"
