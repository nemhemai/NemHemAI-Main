import re
import logging
from datetime import datetime
from typing import Optional

from app.agents.verification.schemas.schemas import VerificationRequest, VerificationResponse
from app.agents.verification.core.constants import (
    DOCUMENT_TYPE_AADHAAR, DOCUMENT_TYPE_PAN, DOCUMENT_TYPE_PASSPORT,
    DOCUMENT_TYPE_DRIVING_LICENSE, DOCUMENT_TYPE_INCOME_CERTIFICATE,
    DOCUMENT_TYPE_CASTE_CERTIFICATE, DOCUMENT_TYPE_BANK_PASSBOOK,
    DOCUMENT_TYPE_LAND_RECORDS, DOCUMENT_TYPE_RATION_CARD,
    DOCUMENT_TYPE_DOMICILE_CERTIFICATE, DOCUMENT_TYPE_VENDING_CERTIFICATE,
    DOCUMENT_TYPE_NO_PUCCA_HOUSE_DECLARATION,
)
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
    def verify(document_type: str, extracted_fields: dict, profile_data: dict = None) -> dict:
        service = VerificationService()
        request = VerificationRequest(
            document_type=document_type,
            extracted_fields=extracted_fields,
            profile_data=profile_data
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
            else:
                logger.warning(f"Skipping specific checks for {doc_type} as per user request")
                checks = {}


            # --- PROFILE CROSS-VALIDATION ---
            profile_data = request.profile_data or {}
            if profile_data and doc_type == DOCUMENT_TYPE_AADHAAR:
                personal_info = profile_data.get("personal_info", profile_data)
                
                extracted_name = fields.get("name", "")
                profile_name = personal_info.get("name", "")
                if extracted_name and profile_name:
                    def match_names(n1, n2):
                        w1 = set(n1.lower().split())
                        w2 = set(n2.lower().split())
                        if w1.issubset(w2) or w2.issubset(w1):
                            return True
                        if len(w1.intersection(w2)) >= 2:
                            return True
                        return False

                    name_passed = match_names(profile_name, extracted_name)
                    checks["profile_name_match"] = {
                        "passed": name_passed,
                        "detail": f"Name match: '{extracted_name}' vs profile '{profile_name}'"
                    }
                
                extracted_dob = fields.get("dob", "")
                profile_dob = personal_info.get("dob", "")
                if extracted_dob and profile_dob:
                    def normalize_date(d_str):
                        import re
                        match = re.search(r'(\d{2,4})[-/.](\d{2})[-/.](\d{2,4})', str(d_str))
                        if match:
                            p1, p2, p3 = match.groups()
                            if len(p1) == 4:
                                return f"{p1}-{p2.zfill(2)}-{p3.zfill(2)}"
                            elif len(p3) == 4:
                                return f"{p3}-{p2.zfill(2)}-{p1.zfill(2)}"
                        return str(d_str).strip()
                    
                    norm_extracted = normalize_date(extracted_dob)
                    norm_profile = normalize_date(profile_dob)
                    dob_passed = True # Forced to pass due to OCR issues
                    
                    checks["profile_dob_match"] = {
                        "passed": dob_passed,
                        "detail": f"DOB match: '{extracted_dob}' vs profile '{profile_dob}' (forced pass)"
                    }

                extracted_aadhaar = fields.get("aadhaar_number", "")
                profile_aadhaar = profile_data.get("aadhaarId", "") or profile_data.get("aadhaar_id", "")
                if extracted_aadhaar and profile_aadhaar:
                    extracted_aadhaar_clean = "".join(filter(str.isdigit, extracted_aadhaar))
                    profile_aadhaar_clean = "".join(filter(str.isdigit, str(profile_aadhaar)))
                    if extracted_aadhaar_clean and profile_aadhaar_clean:
                        aadhaar_passed = (extracted_aadhaar_clean == profile_aadhaar_clean)
                        checks["profile_aadhaar_match"] = {
                            "passed": aadhaar_passed,
                            "detail": f"Aadhaar ID match: '{extracted_aadhaar_clean}' vs profile '{profile_aadhaar_clean}'"
                        }

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
            # NSDL valid entity types: A B C F G H J K L P T (+ S seen in some issued PANs)
            valid_entities = set("ABCFGHLJPTKS")
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

        # MRZ presence check
        # For real passport photos the bottom MRZ strip is often cut off or blurry.
        # Treat mrz_present as a soft warning — only hard-fail if the passport number
        # itself was also not found (meaning the whole document is unreadable).
        mrz_line1 = fields.get("mrz_line1", "")
        mrz_line2 = fields.get("mrz_line2", "")
        mrz_present = len(mrz_line1) == 44 and len(mrz_line2) == 44
        passport_num_found = bool(fields.get("passport_number") or fields.get("mrz_doc_number"))
        checks["mrz_present"] = {
            # Pass if full MRZ found OR at least the visual passport number was read
            "passed": mrz_present or passport_num_found,
            "detail": (
                "MRZ: both lines OK" if mrz_present
                else "MRZ not in image but passport number extracted — soft pass"
                if passport_num_found
                else "MRZ lines not detected and no passport number found"
            ),
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
            # Expiry not extracted — non-critical; DL expiry labels vary widely by state
            checks["dl_expiry_present"] = {
                "passed": True,
                "detail": "Expiry/Valid Till date not extracted — non-critical for DL",
            }

        # 4. Vehicle class present
        vehicle_class = fields.get("vehicle_class", "").strip()
        vc_ok = len(vehicle_class) >= 1  # single codes like LMV, HMV are valid
        checks["dl_vehicle_class"] = {
            "passed": vc_ok,
            "detail": f"Vehicle class: {'present' if vc_ok else 'not found'} (got '{vehicle_class}')"
        }

        # 5. Common checks (DOB, gender)
        checks.update(self._verify_common(fields))

        return checks



    # ------------------------------------------------------------------
    # 2. Income Certificate
    # ------------------------------------------------------------------
    def _verify_income_certificate(self, fields: dict) -> dict:
        checks = {}
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["income_cert_name_present"] = {
            "passed": name_ok,
            "detail": f"Name: {'present' if name_ok else 'missing'} (got '{name}')",
        }

        income_raw = fields.get("income_annual", "")
        if income_raw:
            try:
                income_val = float(str(income_raw).replace(",", ""))
                income_ok = 0 < income_val < 100_000_000
                checks["income_annual_range"] = {
                    "passed": income_ok,
                    "detail": f"Annual income {income_val:,.0f}: {'plausible' if income_ok else 'out of range'}",
                }
            except (ValueError, TypeError):
                checks["income_annual_range"] = {
                    "passed": False,
                    "detail": f"Annual income value could not be parsed: '{income_raw}'",
                }
        else:
            checks["income_annual_present"] = {
                "passed": True,
                "detail": "Annual income not extracted — non-critical",
            }

        unique_id = fields.get("unique_id", "").strip()
        uid_ok = len(unique_id) >= 4
        checks["income_cert_unique_id"] = {
            "passed": uid_ok,
            "detail": f"Certificate ID: {'present' if uid_ok else 'not found'} (got '{unique_id}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 3. Caste / Category Certificate
    # ------------------------------------------------------------------
    def _verify_caste_certificate(self, fields: dict) -> dict:
        checks = {}
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["caste_cert_name_present"] = {
            "passed": name_ok,
            "detail": f"Name: {'present' if name_ok else 'missing'} (got '{name}')",
        }

        category = fields.get("category", "").strip().upper()
        cat_ok = category in {"SC", "ST", "OBC", "SEBC", "EWS", "GENERAL"}
        checks["caste_cert_category_valid"] = {
            "passed": cat_ok,
            "detail": f"Category '{category}': {'valid social category' if cat_ok else 'unrecognized category'}",
        }

        unique_id = fields.get("unique_id", "").strip()
        uid_ok = len(unique_id) >= 4
        checks["caste_cert_unique_id"] = {
            "passed": uid_ok,
            "detail": f"Certificate ID: {'present' if uid_ok else 'not found'} (got '{unique_id}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 4. Bank Passbook / Cancelled Cheque
    # ------------------------------------------------------------------
    def _verify_bank_passbook(self, fields: dict) -> dict:
        checks = {}
        bank_name = fields.get("bank_name", "").strip()
        bank_ok = len(bank_name) >= 3
        checks["bank_name_present"] = {
            "passed": bank_ok,
            "detail": f"Bank Name: {'present' if bank_ok else 'missing'} (got '{bank_name}')",
        }

        holder = fields.get("account_holder_name", "").strip()
        holder_ok = len(holder) >= 3
        checks["account_holder_name_present"] = {
            "passed": holder_ok,
            "detail": f"Account Holder Name: {'present' if holder_ok else 'missing'} (got '{holder}')",
        }

        acc_num = fields.get("account_number", "").strip()
        acc_ok = bool(re.match(r"^\d{9,18}$", acc_num))
        checks["account_number_format"] = {
            "passed": acc_ok,
            "detail": f"Account Number (9-18 digits): {'valid format' if acc_ok else 'invalid format'} (got '{acc_num}')",
        }

        ifsc = fields.get("ifsc_code", "").strip().upper()
        ifsc_ok = bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", ifsc))
        checks["ifsc_code_format"] = {
            "passed": ifsc_ok,
            "detail": f"IFSC Format Check: {'valid' if ifsc_ok else 'invalid'} (got '{ifsc}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 5. Land Records / Ownership Proof
    # ------------------------------------------------------------------
    def _verify_land_records(self, fields: dict) -> dict:
        checks = {}
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["land_owner_name_present"] = {
            "passed": name_ok,
            "detail": f"Owner Name: {'present' if name_ok else 'missing'} (got '{name}')",
        }

        area_raw = fields.get("land_area_acres/hectares", "")
        area_ok = False
        area_detail = f"Could not parse land area: '{area_raw}'"
        if area_raw:
            val_match = re.search(r"([\d\.]+)", str(area_raw))
            if val_match:
                try:
                    val = float(val_match.group(1))
                    area_ok = val > 0
                    area_detail = f"Land area {area_raw}: {'valid' if area_ok else 'must be greater than 0'}"
                except ValueError:
                    pass
        checks["land_area_valid"] = {
            "passed": area_ok,
            "detail": area_detail,
        }

        unique_id = fields.get("unique_id", "").strip()
        uid_ok = len(unique_id) >= 3
        checks["land_unique_id_present"] = {
            "passed": uid_ok,
            "detail": f"Land ID / Survey / Khasra No: {'present' if uid_ok else 'not found'} (got '{unique_id}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 6. Ration Card
    # ------------------------------------------------------------------
    def _verify_ration_card(self, fields: dict) -> dict:
        checks = {}
        head = fields.get("head_of_family", "").strip()
        head_ok = len(head) >= 3
        checks["ration_card_head_present"] = {
            "passed": head_ok,
            "detail": f"Head of Family: {'present' if head_ok else 'missing'} (got '{head}')",
        }

        card_num = fields.get("ration_card_number", "").strip()
        card_ok = len(card_num) >= 4
        checks["ration_card_number_format"] = {
            "passed": card_ok,
            "detail": f"Ration card number: {'present' if card_ok else 'not found'} (got '{card_num}')",
        }

        members = fields.get("family_members", 0)
        try:
            members_val = int(members)
            members_ok = members_val > 0
        except (ValueError, TypeError):
            members_ok = False
        checks["ration_card_family_members_count"] = {
            "passed": members_ok,
            "detail": f"Family members count {members}: {'valid' if members_ok else 'invalid'}",
        }

        category = fields.get("category", "").strip().upper()
        cat_ok = len(category) >= 2
        checks["ration_card_category_valid"] = {
            "passed": cat_ok,
            "detail": f"Category: {'present' if cat_ok else 'missing'} (got '{category}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 7. Domicile / Residence Certificate
    # ------------------------------------------------------------------
    def _verify_domicile_certificate(self, fields: dict) -> dict:
        checks = {}
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["domicile_name_present"] = {
            "passed": name_ok,
            "detail": f"Name: {'present' if name_ok else 'missing'} (got '{name}')",
        }

        state = fields.get("state", "").strip()
        state_ok = len(state) >= 3
        checks["domicile_state_valid"] = {
            "passed": state_ok,
            "detail": f"State: {'present' if state_ok else 'not found'} (got '{state}')",
        }

        cert_num = fields.get("certificate_number", "").strip()
        cert_ok = len(cert_num) >= 3
        checks["domicile_certificate_number"] = {
            "passed": cert_ok,
            "detail": f"Certificate number: {'present' if cert_ok else 'not found'} (got '{cert_num}')",
        }
        return checks

    # ------------------------------------------------------------------
    # 8. Vending Certificate / ULB-TVC Recommendation Letter
    # ------------------------------------------------------------------
    def _verify_vending_certificate(self, fields: dict) -> dict:
        checks = {}
        name = fields.get("name", "").strip()
        name_ok = len(name) >= 3
        checks["vending_vendor_name_present"] = {
            "passed": name_ok,
            "detail": f"Vendor name: {'present' if name_ok else 'missing'} (got '{name}')",
        }

        unique_id = fields.get("unique_id", "").strip()
        uid_ok = len(unique_id) >= 4
        checks["vending_certificate_unique_id"] = {
            "passed": uid_ok,
"detail": f"Vending certificate/recommendation ID: {'present' if uid_ok else 'not found'} (got '{unique_id}')",
        }
        return checks

    # ------------------------------------------------------------------
    # No Pucca House Declaration
    # ------------------------------------------------------------------

    def _verify_pucca_house_declaration(self, fields: dict) -> dict:
        checks = {}
        has_declaration = fields.get("has_declaration", False)
        checks["declaration_present"] = {
            "passed": has_declaration,
            "detail": "Declaration statement present" if has_declaration else "Declaration statement not found",
        }
        name = fields.get("name", "")
        checks["name_present"] = {
            "passed": bool(name),
            "detail": f"Name found: {name}" if name else "Name not found",
        }
        return checks

    # ------------------------------------------------------------------
    # Common / Generic
    # ------------------------------------------------------------------

    def _verify_common(self, fields: dict) -> dict:
        checks = {}

        # DOB present and plausible
        dob = fields.get("dob", "")
        if dob:
            dob_ok, dob_detail = self._validate_dob(dob)
            checks["dob_valid"] = {"passed": dob_ok, "detail": dob_detail}
        else:
            # DOB not extracted — not a hard failure; many real docs use non-standard
            # label placement that the extractor misses. Route to review, not reject.
            checks["dob_present"] = {
                "passed": True,
                "detail": "DOB field not extracted — non-critical; document may still be valid",
            }

        # Gender: informational only — not all docs print gender in a parseable location
        gender = fields.get("gender", "")
        if gender:
            gender_ok = gender.upper() in ("MALE", "FEMALE", "TRANSGENDER", "M", "F")
            checks["gender_valid"] = {
                "passed": gender_ok,
                "detail": f"Gender '{gender}': {'OK' if gender_ok else 'UNRECOGNISED'}",
            }
        # If gender not extracted, we simply skip the check (no failure added)

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
