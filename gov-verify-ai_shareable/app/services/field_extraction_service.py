import re
import logging
from typing import Optional

from app.schemas.schemas import FieldExtractionRequest, FieldExtractionResponse
from app.core.constants import DOCUMENT_TYPE_AADHAAR, DOCUMENT_TYPE_PAN, DOCUMENT_TYPE_PASSPORT, DOCUMENT_TYPE_DRIVING_LICENSE
from app.core.exceptions import FieldExtractionError
from app.core.logger import get_logger

logger = get_logger(__name__)


import uuid

class FieldExtractionService:
    """
    Extracts structured fields from raw OCR text based on document type.
    Supports Aadhaar, PAN, and Passport documents.
    """

    @staticmethod
    def extract_fields(document_type: str, extracted_text: str) -> dict:
        service = FieldExtractionService()
        request = FieldExtractionRequest(
            document_type=document_type,
            extracted_text=extracted_text
        )
        res = service.extract(request)
        return res.model_dump()

    def extract(self, request: FieldExtractionRequest) -> FieldExtractionResponse:
        logger.info(f"Starting field extraction for doc_type={request.document_type}")

        text = request.extracted_text or ""
        doc_type = (request.document_type or "").upper()

        try:
            if doc_type == DOCUMENT_TYPE_AADHAAR:
                fields = self._extract_aadhaar_fields(text)
            elif doc_type == DOCUMENT_TYPE_PAN:
                fields = self._extract_pan_fields(text)
            elif doc_type == DOCUMENT_TYPE_PASSPORT:
                fields = self._extract_passport_fields(text)
            elif doc_type == DOCUMENT_TYPE_DRIVING_LICENSE:
                fields = self._extract_dl_fields(text)
            else:
                logger.warning(f"Unsupported doc_type: {doc_type}. Attempting generic extraction.")
                fields = self._extract_generic_fields(text)

            logger.info(f"Field extraction complete: {list(fields.keys())}")
            return FieldExtractionResponse(
                request_id=str(uuid.uuid4()),
                document_type=doc_type,
                extracted_fields=fields,
                status="SUCCESS",
                raw_text=text,
                success=True
            )

        except Exception as e:
            logger.error(f"Field extraction failed: {e}", exc_info=True)
            raise FieldExtractionError(f"Field extraction error: {str(e)}")

    # ------------------------------------------------------------------
    # Aadhaar
    # ------------------------------------------------------------------

    def _extract_aadhaar_fields(self, text: str) -> dict:
        fields = {}

        # Aadhaar number: 12 digits, often space-separated as XXXX XXXX XXXX
        aadhaar_match = re.search(
            r"\b(\d{4}[\s\-]?\d{4}[\s\-]?\d{4})\b", text
        )
        if aadhaar_match:
            fields["aadhaar_number"] = re.sub(r"[\s\-]", "", aadhaar_match.group(1))

        # Date of Birth
        dob = self._extract_dob(text)
        if dob:
            fields["dob"] = dob

        # Gender
        gender = self._extract_gender(text)
        if gender:
            fields["gender"] = gender

        # Name (line above DOB or after "Name:")
        name = self._extract_name(text, doc_type=DOCUMENT_TYPE_AADHAAR)
        if name:
            fields["name"] = name

        # Address (everything after "Address" keyword)
        address_match = re.search(
            r"(?:Address|addr)[:\s]+(.+?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL
        )
        if address_match:
            fields["address"] = address_match.group(1).strip().replace("\n", ", ")

        return fields

    # ------------------------------------------------------------------
    # PAN
    # ------------------------------------------------------------------

    def _extract_pan_fields(self, text: str) -> dict:
        fields = {}

        # PAN number: [A-Z]{5}[0-9]{4}[A-Z]
        pan_match = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", text)
        if pan_match:
            fields["pan_number"] = pan_match.group(1)

        # Date of Birth
        dob = self._extract_dob(text)
        if dob:
            fields["dob"] = dob

        # Name (usually on its own line near top)
        name = self._extract_name(text, doc_type=DOCUMENT_TYPE_PAN)
        if name:
            fields["name"] = name

        # Father's Name (PAN cards include this)
        father_match = re.search(
            r"(?:Father'?s?\s+Name|S/O|D/O)[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE
        )
        if father_match:
            fields["father_name"] = father_match.group(1).strip()

        return fields

    # ------------------------------------------------------------------
    # Passport
    # ------------------------------------------------------------------

    def _extract_passport_fields(self, text: str) -> dict:  # noqa: C901
        fields = {}
        lines = [l.strip() for l in text.splitlines()]

        # ------------------------------------------------------------------
        # 1. Passport number: 1 letter + 7 digits (India)
        # ------------------------------------------------------------------
        passport_match = re.search(r"\b([A-Z][0-9]{7})\b", text)
        if passport_match:
            fields["passport_number"] = passport_match.group(1)

        # ------------------------------------------------------------------
        # 2. MRZ lines (TD3 format: two 44-char lines)
        #    MRZ is the most reliable source — parse it FIRST.
        # ------------------------------------------------------------------
        mrz_lines = re.findall(r"[A-Z0-9<]{44}", text)
        # Also look for a partial MRZ line 1 (at least 10 chars, starts with P<)
        mrz_line1_partial = re.search(r"P<[A-Z]{3}[A-Z<]{5,}", text)

        checks = {}
        if len(mrz_lines) >= 2:
            fields["mrz_line1"] = mrz_lines[0]
            fields["mrz_line2"] = mrz_lines[1]
            fields.update(self._parse_mrz(mrz_lines[0], mrz_lines[1]))
        elif len(mrz_lines) == 1:
            line2 = mrz_lines[0]
            fields["mrz_line2"] = line2
            try:
                # MRZ presence (informational — partial MRZ from truncated photos is OK)
                mrz_line1 = fields.get("mrz_line1", "")
                mrz_line2 = fields.get("mrz_line2", "")
                # Accept: both lines 44 chars (full MRZ) OR line 2 alone (line 1 OCR-truncated)
                mrz_line1_ok = len(mrz_line1) == 44
                mrz_line2_ok = len(mrz_line2) == 44
                mrz_present = mrz_line1_ok and mrz_line2_ok
                mrz_any     = mrz_line1_ok or mrz_line2_ok  # at least one line
                checks["mrz_present"] = {
                    # Only hard-fail if NEITHER line is present at all
                    "passed": mrz_any,
                    "detail": (
                        "MRZ: both lines OK" if mrz_present
                        else "MRZ: line 2 only (line 1 truncated in photo)" if mrz_line2_ok
                        else "MRZ: line 1 only" if mrz_line1_ok
                        else "MRZ lines: not detected in image"
                    ),
                }
                fields.update(self._parse_mrz("P" + "<" * 43, line2))
            except Exception:
                pass

        # Parse name from partial MRZ line 1 (e.g. OCR truncated it but name is still there)
        if mrz_line1_partial and not fields.get("mrz_name"):
            raw = mrz_line1_partial.group(0)
            # Skip P<CCC (5 chars), rest is SURNAME<<GIVEN...
            name_field = raw[5:].rstrip("<")
            if "<<" in name_field:
                parts = name_field.split("<<")
                surname   = parts[0].replace("<", " ").strip()
                given     = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
                full = f"{given} {surname}".strip() if given else surname
            else:
                full = name_field.replace("<", " ").strip()
            if full:
                fields["mrz_name"] = re.sub(r"\s+", " ", full)

        # ------------------------------------------------------------------
        # 3. Date helpers
        # ------------------------------------------------------------------
        MONTH_MAP = {
            "jan": "01", "feb": "02", "mar": "03", "apr": "04",
            "may": "05", "jun": "06", "jul": "07", "aug": "08",
            "sep": "09", "oct": "10", "nov": "11", "dec": "12",
        }
        _DATE_RE = re.compile(
            r"(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
            r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}"
            r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}[,\s]+\d{4})",
            re.IGNORECASE
        )

        def _norm(raw: str) -> Optional[str]:
            """Normalise a date string to DD/MM/YYYY (accepts future dates)."""
            raw = raw.strip()
            m = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})$", raw)
            if m:
                dd, mm, yy = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
                if len(yy) == 2:
                    yr = int(yy)
                    yy = str(1900 + yr) if yr >= 30 else str(2000 + yr)
                return f"{dd}/{mm}/{yy}"
            m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(\d{4})$", raw)
            if m:
                mm2 = MONTH_MAP.get(m.group(2).lower()[:3], "")
                if mm2:
                    return f"{m.group(1).zfill(2)}/{mm2}/{m.group(3)}"
            m = re.match(r"^([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})[,\s]+(\d{4})$", raw)
            if m:
                mm2 = MONTH_MAP.get(m.group(1).lower()[:3], "")
                if mm2:
                    return f"{m.group(2).zfill(2)}/{mm2}/{m.group(3)}"
            return None

        # ------------------------------------------------------------------
        # 4. Line-by-line ordered pairing for Issue / Expiry dates
        # ------------------------------------------------------------------
        # Indian passport layout — OCR sees labels and values on separate lines:
        #   "Date oflssue"      "/Date af Expiry"   <- garbled labels
        #   "20/06/2023"        "19/06/2033"        <- clean date values
        #
        # Strategy: collect label lines in order, then date-value lines that
        # appear AFTER the labels in the same order, and pair them 1-to-1.
        # ------------------------------------------------------------------

        def _is_expiry_label(line: str) -> bool:
            lc = line.lower()
            return bool(
                re.search(r"expir", lc) or
                re.search(r"valid.{0,6}(till|until|upto)", lc)
            )

        def _is_issue_label(line: str) -> bool:
            lc = line.lower()
            al = re.sub(r"[^a-z0-9]", "", lc)
            # Must look like some variant of "Date of ..."
            has_date_of = bool(
                re.search(r"date\s*of\w*", lc) or   # "Date of...", "Date ofss", "DateofExpiry"
                re.search(r"\bdate\s+of\b", lc) or  # "Date of" with word boundary
                re.search(r"dateof", al)              # compact: "dateoflssue", "dateofss"
            )
            if not has_date_of:
                return False
            # Must NOT be expiry or birth/death labels
            if _is_expiry_label(line):
                return False
            if re.search(r"birth|bir|death", lc):
                return False
            # Any other "Date of..." = Issue label
            return True

        label_sequence = []   # [('issue'|'expiry', line_idx), ...]
        for idx, line in enumerate(lines):
            if _is_issue_label(line):
                label_sequence.append(("issue", idx))
            elif _is_expiry_label(line):
                label_sequence.append(("expiry", idx))

        # Check if dates are inline (on the same line as the label)
        # e.g. "Date of Issue: 20/06/2023"
        # vs. separate lines: "Date of Issue" \n "20/06/2023"
        issue_date: Optional[str] = None
        expiry_date: Optional[str] = None

        for ltype, idx in label_sequence:
            dm = _DATE_RE.search(lines[idx])
            if dm:
                # Inline: date is on the same line as the label
                nd = _norm(dm.group(0))
                if nd:
                    if ltype == "issue":
                        issue_date = nd
                    elif ltype == "expiry":
                        expiry_date = nd

        # If inline extraction didn't find both dates, fall back to ordered pairing
        # (labels on one line, date values on subsequent separate lines)
        if not (issue_date or expiry_date):
            first_lbl_idx = label_sequence[0][1] if label_sequence else len(lines)
            date_values = []   # [(line_idx, normed_date), ...]
            for idx in range(first_lbl_idx + 1, len(lines)):
                dm = _DATE_RE.search(lines[idx])
                if dm:
                    nd = _norm(dm.group(0))
                    if nd:
                        date_values.append((idx, nd))

            for i, (ltype, _) in enumerate(label_sequence):
                if i < len(date_values):
                    if ltype == "issue":
                        issue_date = date_values[i][1]
                    elif ltype == "expiry":
                        expiry_date = date_values[i][1]

        if issue_date:
            fields["issue_date"] = issue_date
        if expiry_date:
            fields["expiry_date"] = expiry_date

        # MRZ expiry is AUTHORITATIVE — always overrides visual extraction
        if fields.get("mrz_expiry"):
            fields["expiry_date"] = fields["mrz_expiry"]

        # ------------------------------------------------------------------
        # 5. Date of Birth
        #    MRZ DOB is authoritative. Fallback: scrub issue/expiry from text.
        # ------------------------------------------------------------------
        if fields.get("mrz_dob"):
            fields["dob"] = fields["mrz_dob"]
        else:
            scrubbed = text
            for d in [issue_date, expiry_date]:
                if d:
                    scrubbed = scrubbed.replace(d, "")
            dob = self._extract_dob(scrubbed)
            if dob:
                fields["dob"] = dob

        # ------------------------------------------------------------------
        # 6. Nationality — look for INDIAN / IND keyword directly
        # ------------------------------------------------------------------
        if re.search(r"\b(INDIAN|IND)\b", text, re.IGNORECASE):
            fields["nationality"] = "INDIAN"

        # ------------------------------------------------------------------
        # 7. Name
        #    Priority: (a) visual Surname+Given Names labels (most accurate,
        #              gives GIVEN SURNAME order), (b) MRZ name, (c) generic
        # ------------------------------------------------------------------

        # (a) Visual Surname + Given Names label extraction
        # Indian passport OCR layout:
        #   "Surname"     → next line = SURNAME
        #   "Given Names" → next line = GIVEN NAMES
        surname_val = given_val = None
        for idx, line in enumerate(lines):
            lc = line.lower()
            if re.search(r"sur\s*name|suname", lc) and idx + 1 < len(lines):
                cand = lines[idx + 1].strip()
                if re.match(r"^[A-Z][A-Z ]{1,39}$", cand):
                    surname_val = cand
            if re.search(r"given\s*name", lc) and idx + 1 < len(lines):
                cand = lines[idx + 1].strip()
                if re.match(r"^[A-Z][A-Z ]{1,39}$", cand):
                    given_val = cand

        if given_val and surname_val:
            fields["name"] = f"{given_val} {surname_val}"
        elif surname_val:
            fields["name"] = surname_val
        elif given_val:
            fields["name"] = given_val

        # (b) MRZ name fallback (surname-first format from MRZ)
        if not fields.get("name") and fields.get("mrz_name"):
            fields["name"] = fields["mrz_name"]

        # (c) Generic visual extraction fallback
        if not fields.get("name"):
            name = self._extract_name(text, doc_type=DOCUMENT_TYPE_PASSPORT)
            if name:
                fields["name"] = name


        return fields


    # ------------------------------------------------------------------
    # Generic
    # ------------------------------------------------------------------

    def _extract_generic_fields(self, text: str) -> dict:
        fields = {}
        dob = self._extract_dob(text)
        if dob:
            fields["dob"] = dob
        name = self._extract_name(text, doc_type="GENERIC")
        if name:
            fields["name"] = name
        return fields

    # ------------------------------------------------------------------
    # Driving License
    # ------------------------------------------------------------------

    def _extract_dl_fields(self, text: str) -> dict:
        fields = {}

        # DL Number: Indian format e.g. MH-12-20230012345 or MH0120230012345
        dl_match = (
            re.search(r"\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{7})\b", text) or
            re.search(r"\b([A-Z]{2}[-\s]?\d{2}[-\s]?\d{4}[-\s]?\d{6})\b", text) or
            re.search(r"\b([A-Z]{2}\d{13,15})\b", text)
        )
        if dl_match:
            fields["dl_number"] = re.sub(r"[\s]", "", dl_match.group(1))

        # Name
        name = self._extract_name(text, doc_type=DOCUMENT_TYPE_DRIVING_LICENSE)
        if name:
            fields["name"] = name

        # Date of Birth
        dob = self._extract_dob(text)
        if dob:
            fields["dob"] = dob

        # Gender
        gender = self._extract_gender(text)
        if gender:
            fields["gender"] = gender

        # Address
        address_match = re.search(
            r"(?:Address|Addr|ADD)[:\s]+(.+?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL
        )
        if address_match:
            fields["address"] = address_match.group(1).strip().replace("\n", ", ")

        # Vehicle Class (COV / Class of Vehicle)
        cov_match = re.search(
            r"(?:COV|Class of Vehicle|Vehicle Class|Authorisation)[:\s]+([A-Z0-9,\s/]+)",
            text, re.IGNORECASE
        )
        if cov_match:
            fields["vehicle_class"] = cov_match.group(1).strip()
        else:
            # Try to find vehicle class codes inline (LMV, HMV, MCWG, MCWOG, etc.)
            cov_inline = re.findall(
                r"\b(LMV|HMV|MCWG|MCWOG|TRANS|HGMV|HPMV|MGV|PSV|LDRXCV)\b", text, re.IGNORECASE
            )
            if cov_inline:
                fields["vehicle_class"] = ", ".join(set(c.upper() for c in cov_inline))

        # Blood Group
        blood_match = re.search(
            r"(?:Blood\s*Group|Blood)[:\s]*([ABO]{1,2}[+-]|AB[+-])",
            text, re.IGNORECASE
        )
        if blood_match:
            fields["blood_group"] = blood_match.group(1).strip().upper()

        # Expiry / Valid Till date
        expiry_match = re.search(
            r"(?:Valid\s*(?:Till|Until|Upto)|Expiry\s*Date|Validity|Expires?)[:\s]+([\d]{1,2}[/\-\.][\d]{1,2}[/\-\.][\d]{2,4})",
            text, re.IGNORECASE
        )
        if expiry_match:
            fields["expiry_date"] = expiry_match.group(1).strip()

        # Issue Date
        issue_match = re.search(
            r"(?:Date\s*of\s*Issue|Issue\s*Date|Issued\s*On|DOI)[:\s]+([\d]{1,2}[/\-\.][\d]{1,2}[/\-\.][\d]{2,4})",
            text, re.IGNORECASE
        )
        if issue_match:
            fields["issue_date"] = issue_match.group(1).strip()

        # Issuing Authority / RTO
        rto_match = re.search(
            r"(?:Issuing Authority|Issued By|RTO|Licensing Authority)[:\s]+([A-Za-z\s,\.]+)",
            text, re.IGNORECASE
        )
        if rto_match:
            fields["issuing_rto"] = rto_match.group(1).strip()

        return fields

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Month name correction table for common Indian OCR misreads
    # ------------------------------------------------------------------
    _MONTH_OCR_FIX = {
        # Common OCR errors for month abbreviations
        "JAM": "JAN", "JAN": "JAN",
        "FEB": "FEB", "FEE": "FEB", "FEB": "FEB",
        "MAR": "MAR", "MAS": "MAR",
        "APR": "APR", "APB": "APR",
        "MAY": "MAY",
        "JUN": "JUN", "JUM": "JUN",
        "JUL": "JUL", "JOL": "JUL",
        "AUG": "AUG", "AUQ": "AUG", "AUS": "AUG",
        "SEP": "SEP", "SEF": "SEP",
        "OCT": "OCT", "OCI": "OCT",
        "NOV": "NOV", "MOV": "NOV",
        "DEC": "DEC", "DES": "DEC",
        # Full names
        "JANUARY": "JAN", "FEBRUARY": "FEB", "MARCH": "MAR",
        "APRIL": "APR", "JUNE": "JUN", "JULY": "JUL",
        "AUGUST": "AUG", "SEPTEMBER": "SEP", "OCTOBER": "OCT",
        "NOVEMBER": "NOV", "DECEMBER": "DEC",
    }

    def _extract_dob(self, text: str) -> Optional[str]:  # noqa: C901
        """
        Robust DOB extractor for Indian government documents (Aadhaar, PAN, Passport,
        Driving License). Handles:
          - English & Hindi label prefixes (DOB, Date of Birth, जन्म तिथि, YOB, etc.)
          - Separator formats: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, YYYY-MM-DD
          - Month-name formats: 08 Aug 1990, 08-AUG-1990, August 08, 1990
          - No-separator 8-digit strings: DDMMYYYY, YYYYMMDD
          - 6-digit compact forms: DDMMYY, YYMMDD
          - Year-only Aadhaar: "Year of Birth: 1990"
          - OCR misread correction for month abbreviations
          - Sanity check: date must be between 1900-01-01 and today
        """
        from datetime import datetime, date

        today = date.today()
        current_year = today.year

        # ----------------------------------------------------------------
        # Helper: try to parse a normalised DD/MM/YYYY-style string
        # ----------------------------------------------------------------
        def _try_parse(s: str) -> Optional[str]:
            """Try several strptime formats on a normalised string and
            return 'DD/MM/YYYY' on the first success, else None."""
            for fmt in (
                "%d/%m/%Y", "%Y/%m/%d",      # full-year separators
                "%d/%m/%y", "%y/%m/%d",      # 2-digit year separators
                "%d/%b/%Y", "%d/%b/%y",      # month-name variants
                "%b/%d/%Y", "%B/%d/%Y",      # US-style month-name
            ):
                try:
                    dt = datetime.strptime(s, fmt)
                    # Fix Python's strptime 2-digit year interpretation
                    if dt.year < 100:
                        # years 00-25 → 2000-2025; 26-99 → 1926-1999
                        dt = dt.replace(year=dt.year + (2000 if dt.year <= 25 else 1900))
                    if 1900 <= dt.year <= current_year:
                        return dt.strftime("%d/%m/%Y")
                except ValueError:
                    continue
            return None

        # ----------------------------------------------------------------
        # Helper: fix OCR-mangled month abbreviations, then try parse
        # ----------------------------------------------------------------
        def _fix_month_and_parse(raw: str) -> Optional[str]:
            """Normalise separators and correct OCR month-name errors."""
            # Normalise all separators to '/'
            # NOTE: commas are included so "August 15, 1990" -> "August/15/1990"
            normed = re.sub(r"[\s\-\.,]", "/", raw.strip()).upper()
            # Collapse consecutive slashes (e.g. "15,/1990" -> "15/1990")
            normed = re.sub(r"/+", "/", normed)
            # Remove leading/trailing slashes
            normed = normed.strip("/")

            # Attempt direct parse first
            result = _try_parse(normed)
            if result:
                return result

            # Try correcting 3-letter month tokens
            parts = normed.split("/")
            corrected_parts = []
            for p in parts:
                corrected_parts.append(self._MONTH_OCR_FIX.get(p, p))
            corrected = "/".join(corrected_parts)
            if corrected != normed:
                result = _try_parse(corrected)
                if result:
                    return result

            # NOTE: We intentionally do NOT auto-swap DD and MM.
            # Indian government documents always use DD/MM/YYYY order.
            # Auto-swapping would silently convert an invalid month value
            # (e.g. month=13) into a spurious valid date.
            return None

        # ----------------------------------------------------------------
        # Helper: parse bare 8-digit DDMMYYYY / YYYYMMDD string
        # ----------------------------------------------------------------
        def _parse_8digit(s: str) -> Optional[str]:
            for fmt in ("%d%m%Y", "%Y%m%d"):
                try:
                    dt = datetime.strptime(s, fmt)
                    if 1900 <= dt.year <= current_year:
                        return dt.strftime("%d/%m/%Y")
                except ValueError:
                    continue
            return None

        # ----------------------------------------------------------------
        # Helper: parse bare 6-digit DDMMYY / YYMMDD string
        # ----------------------------------------------------------------
        def _parse_6digit(s: str) -> Optional[str]:
            for fmt in ("%d%m%y", "%y%m%d"):
                try:
                    dt = datetime.strptime(s, fmt)
                    if dt.year > current_year:
                        dt = dt.replace(year=dt.year - 100)
                    if 1900 <= dt.year <= current_year:
                        return dt.strftime("%d/%m/%Y")
                except ValueError:
                    continue
            return None

        # ================================================================
        # STEP 1 – Label-anchored extraction (highest confidence)
        # Supports both English and Hindi DOB labels commonly found on
        # Indian government documents.  Uses re.DOTALL so the date may
        # appear on the next line.
        # ================================================================

        # English labels  (DOB, Date of Birth, D.O.B, Birth Date, Born, YOB, Year of Birth)
        # Hindi labels    (जन्म तिथि, जन्म दिनांक, जन्म)
        LABEL_RE = (
            r"(?:"
            r"D\.?\s*O\.?\s*B\.?"                           # D.O.B / DOB
            r"|Date\s+of\s+Birth"                           # Date of Birth
            r"|Birth\s+Date"                                # Birth Date
            r"|Born"                                        # Born
            r"|YOB"                                         # Year of Birth (Aadhaar)
            r"|Year\s+of\s+Birth"                           # Year of Birth
            r"|जन्म\s*(?:तिथि|दिनांक|दिन)?"              # Hindi: जन्म तिथि / जन्म
            r")"
            r"[\s:.\-\/|]*"                                 # separator between label & value
        )

        # Pattern A – label + separateed date (with digit or month-name parts)
        # Covers: "DOB: 08/08/1990", "Date of Birth: 08 Aug 1990", "DOB: 1990-08-08"
        LABEL_DATE_WITH_SEP = (
            LABEL_RE
            + r"(\d{1,2}[\s\/\-\.]\d{1,2}[\s\/\-\.]\d{2,4}"   # DD sep MM sep YYYY
            + r"|\d{4}[\s\/\-\.]\d{1,2}[\s\/\-\.]\d{1,2}"      # YYYY sep MM sep DD
            + r"|\d{1,2}[\s\/\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
            +   r"|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
            +   r"|JAM|FEE|MAS|APB|JUM|JOL|AUQ|AUS|SEF|OCI|MOV|DES"  # OCR variants
            +   r"|January|February|March|April|June|July|August|September|October|November|December"
            + r")[\s\/\-\.]\d{2,4})"                            # day-monthname-year
        )

        # Pattern B – label + 8-digit date without separators
        LABEL_DATE_8DIGIT = LABEL_RE + r"(\d{8})"

        # Pattern C – label + 6-digit date without separators
        LABEL_DATE_6DIGIT = LABEL_RE + r"(\d{6})"

        # Pattern D – YOB / Year-of-Birth label + 4-digit year only (Aadhaar front)
        LABEL_YEAR_ONLY = (
            r"(?:YOB|Year\s+of\s+Birth)"
            r"[\s:.\-\/|]*"
            r"(\d{4})"
        )

        for pattern, handler_tag in [
            (LABEL_DATE_WITH_SEP, "sep"),
            (LABEL_DATE_8DIGIT,   "8d"),
            (LABEL_DATE_6DIGIT,   "6d"),
            (LABEL_YEAR_ONLY,     "year"),
        ]:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                raw = match.group(1).strip()
                if handler_tag == "sep":
                    result = _fix_month_and_parse(raw)
                    if result:
                        return result
                elif handler_tag == "8d":
                    digits = re.sub(r"\D", "", raw)
                    result = _parse_8digit(digits)
                    if result:
                        return result
                elif handler_tag == "6d":
                    digits = re.sub(r"\D", "", raw)
                    result = _parse_6digit(digits)
                    if result:
                        return result
                elif handler_tag == "year":
                    yr = int(raw)
                    if 1900 <= yr <= current_year:
                        return f"01/01/{yr}"

        # ================================================================
        # STEP 2 – Unlabelled date-with-separators (fallback)
        # Only match dates whose year part is in [1900, current_year].
        # We avoid matching Aadhaar/phone/PAN numbers by requiring the
        # year portion to look like a calendar year.
        # ================================================================

        # Ordered from most-specific to least-specific to avoid false positives
        STANDALONE_PATTERNS = [
            # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY (most common on Indian IDs)
            r"(?<!\d)(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.](?:19|20)\d{2})(?!\d)",
            # YYYY/MM/DD or YYYY-MM-DD (ISO-ish)
            r"(?<!\d)((?:19|20)\d{2}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})(?!\d)",
            # DD MonthName YYYY  e.g. "08 Aug 1990", "08-AUG-1990"
            (r"(?<!\d)(\d{1,2}[\s\-\/\.]"
             r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
             r"|JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC"
             r"|JAM|FEE|MAS|APB|JUM|JOL|AUQ|AUS|SEF|OCI|MOV|DES"
             r"|January|February|March|April|June|July|August|September|October|November|December"
             r")[\s\-\/\.](?:19|20)\d{2})(?!\d)"),
            # MonthName DD, YYYY  e.g. "August 08, 1990" (some DL/Passport printouts)
            (r"(?<!\d)((?:January|February|March|April|May|June|July|August|September|October|November|December)"
             r"[\s\-\/\.]\d{1,2}[,\s\-\/\.]+(?:19|20)\d{2})(?!\d)"),
            # Compact DD/MM/YY with 2-digit year
            r"(?<!\d)(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2})(?!\d)",
            # 8-digit compact: only match if surrounded by whitespace/start/end (avoid Aadhaar)
            r"(?<!\d)(\d{8})(?!\d)",
        ]

        for pattern in STANDALONE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                # 8-digit special handling
                digits_only = re.sub(r"\D", "", raw)
                if len(digits_only) == 8 and not re.search(r"[a-zA-Z]", raw):
                    result = _parse_8digit(digits_only)
                    if result:
                        return result
                else:
                    result = _fix_month_and_parse(raw)
                    if result:
                        return result

        return None

    def _extract_gender(self, text: str) -> Optional[str]:
        match = re.search(
            r"\b(Male|Female|MALE|FEMALE|M|F|Transgender|TRANSGENDER)\b", text
        )
        if match:
            raw = match.group(1).upper()
            if raw in ("M", "MALE"):
                return "MALE"
            if raw in ("F", "FEMALE"):
                return "FEMALE"
            return raw
        return None

    def _extract_name(self, text: str, doc_type: str = "GENERIC") -> Optional[str]:
        from difflib import get_close_matches

        # 1. Try explicit label first — also handles Hindi/bilingual labels like "नाम/Name"
        label_match = re.search(
            r"(?:(?:[^\n]*/)?(?:Name|Full Name))[:\s\t\r\n]+([A-Za-z][A-Za-z \t\.\'-]{2,49})",
            text, re.IGNORECASE
        )
        if label_match:
            val = label_match.group(1).strip()
            # Reject if it looks like it starts another label
            if not re.search(r"(?:Father|Mother|Husband|Signature|Date|Birth|Addr)", val, re.IGNORECASE):
                return re.sub(r"\s+", " ", val)

        # 2. Prepare lines and filter out forbidden/noisy lines
        forbidden_words = {
            "government", "india", "unique", "identification", "authority", "uidai",
            "income", "tax", "department", "republic", "passport", "driving", "licence",
            "license", "transport", "union", "territory", "state", "card", "identity",
            "dob", "date", "birth", "year", "gender", "male", "female", "transgender",
            "father", "mother", "husband", "wife", "address", "enrollment", "registration",
            "signature", "holder", "valid", "expiry", "issue", "rto", "national", "regional",
            "director", "commissioner", "deputy", "office", "official", "ministry", "home",
            "affairs", "permanent", "account", "number", "cardholder", "validity", "issued",
            "belgique", "belgium", "royaume", "kingdom", "nationalite", "nationality",
            "signature", "holder", "pasport", "travel", "document", "surname", "given", "names",
            "govt", "of"
        }

        def is_valid_name_candidate(line: str) -> bool:
            line_clean = line.strip()
            if not line_clean:
                return False
            # Must start with letter, only contain letters, spaces, dots, single quotes, hyphens
            if not re.match(r"^[A-Za-z][A-Za-z \t\.\'-]{3,45}$", line_clean):
                return False
            # Check number of words (must be >= 2)
            words = line_clean.split()
            if len(words) < 2:
                return False
            # Check for forbidden words — exact AND fuzzy match (catches OCR misreads
            # like "Pemanent" for "Permanent", "Accoud" for "Account" etc.)
            for w in words:
                wl = w.lower()
                if wl in forbidden_words:
                    return False
                # Fuzzy match: reject if any forbidden word is >=80% similar
                if get_close_matches(wl, forbidden_words, n=1, cutoff=0.80):
                    return False
            # Average word length should be >= 2.5
            avg_len = sum(len(w) for w in words) / len(words)
            if avg_len < 2.5:
                return False
            return True

        lines = [line.strip() for line in text.splitlines()]
        
        # 3. Proximity search: find lines containing DOB, Gender, or Aadhaar/PAN pattern
        # and look at lines above them.
        anchor_indices = []
        for i, line in enumerate(lines):
            # Keyword anchors
            if re.search(r"\b(dob|birth|yob|born|gender)\b", line, re.IGNORECASE):
                anchor_indices.append(i)
            # Loose gender match for OCR errors like "dFEMALE"
            elif re.search(r"(male|female|m/f)", line, re.IGNORECASE):
                anchor_indices.append(i)
            # Aadhaar number
            elif re.search(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b", line):
                anchor_indices.append(i)
            # PAN number
            elif re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", line):
                anchor_indices.append(i)
            # Date format anchor (e.g. 15/07/2004) to catch unlabeled DOBs
            elif re.search(r"\d{2}[\/\-\.]\d{2}[\/\-\.]\d{2,4}", line):
                anchor_indices.append(i)

        for anchor_idx in anchor_indices:
            candidates = []

            # Look ABOVE the anchor (default for most doc types)
            for offset in range(1, 5):
                prev_idx = anchor_idx - offset
                if prev_idx >= 0:
                    cand = lines[prev_idx]
                    if is_valid_name_candidate(cand):
                        candidates.append(("above", offset, cand))

            # For PAN cards: also look BELOW the anchor — on PAN cards the name
            # comes AFTER the PAN number (layout: PAN → Name label → Name → Father)
            if doc_type == DOCUMENT_TYPE_PAN:
                for offset in range(1, 6):
                    next_idx = anchor_idx + offset
                    if next_idx < len(lines):
                        cand = lines[next_idx]
                        if is_valid_name_candidate(cand):
                            candidates.append(("below", offset, cand))

            if candidates:
                # For PAN: prefer lines BELOW the PAN number (holder name comes first)
                if doc_type == DOCUMENT_TYPE_PAN:
                    below = [(d, o, c) for d, o, c in candidates if d == "below"]
                    if below:
                        below.sort(key=lambda x: x[1])  # closest first
                        return re.sub(r"\s+", " ", below[0][2])
                # Default: return the closest valid candidate above
                above = [(d, o, c) for d, o, c in candidates if d == "above"]
                if above:
                    above.sort(key=lambda x: x[1])
                    return re.sub(r"\s+", " ", above[0][2])

        # 4. Fallback: Search all lines globally and return the first valid candidate
        for line in lines:
            if is_valid_name_candidate(line):
                return re.sub(r"\s+", " ", line)

        return None

    def _parse_mrz(self, line1: str, line2: str) -> dict:
        """Parse TD3 MRZ format (passport, 44-char lines)."""
        mrz_fields = {}
        try:
            # Line 1: P<ISOSURNAME<<GIVENNAME...
            if line1.startswith("P"):
                country = line1[2:5]
                name_raw = line1[5:44].replace("<", " ").strip()
                mrz_fields["mrz_country"] = country
                mrz_fields["mrz_name"] = re.sub(r"\s+", " ", name_raw)

            # Line 2: passport_no + check + country + dob + check + sex + expiry + check + ...
            doc_number = line2[0:9].replace("<", "")
            dob_raw = line2[13:19]  # YYMMDD
            sex = line2[20]
            expiry_raw = line2[21:27]  # YYMMDD

            mrz_fields["mrz_doc_number"] = doc_number

            # Expand 2-digit MRZ years to 4-digit
            # DOB: yy >= 30 → 19xx (born before 2030), else → 20xx
            # Expiry: always → 20xx (passports never expire in the past century)
            import datetime
            current_year = datetime.datetime.now().year

            def _mrz_dob_year(yy: str) -> str:
                y = int(yy)
                return str(1900 + y) if y >= 30 else str(2000 + y)

            def _mrz_exp_year(yy: str) -> str:
                y = int(yy)
                # Expiry is always in the future — use 20xx
                return str(2000 + y)

            dob_dd = dob_raw[4:6]
            dob_mm = dob_raw[2:4]
            dob_yy = dob_raw[0:2]
            mrz_fields["mrz_dob"] = f"{dob_dd}/{dob_mm}/{_mrz_dob_year(dob_yy)}"

            mrz_fields["mrz_sex"] = sex

            exp_dd = expiry_raw[4:6]
            exp_mm = expiry_raw[2:4]
            exp_yy = expiry_raw[0:2]
            mrz_fields["mrz_expiry"] = f"{exp_dd}/{exp_mm}/{_mrz_exp_year(exp_yy)}"
        except Exception as e:
            logger.warning(f"MRZ parse partial failure: {e}")
        return mrz_fields
