from importlib import metadata

from app.utils.noise_utils import is_noise, compile_noise_patterns


class ExtractionValidator:

    def __init__(self):
        self.noise_patterns = compile_noise_patterns()
        
    def _is_element_corrupted(self, text):

        if not text:
            return True

        text = text.strip()

        # too many weird characters
        weird_ratio = sum(1 for c in text if not (c.isalnum() or c.isspace() or '\u0900' <= c <= '\u097F')) / max(len(text), 1)

        if weird_ratio > 0.4:
            return True

        # very short but high token count mismatch
        if len(text) < 5:
            return True

        return False

    def transform(self, elements, document_id=None):

        enriched = []
        debug = DebugCollector(document_id)

        for e in elements:

            # ---------------------------------------
            # 🔥 STEP 1 — SKIP INVALID ELEMENTS
            # ---------------------------------------
            if not isinstance(e, dict):
                continue

            # ---------------------------------------
            # 🔥 STEP 2 — FIX METADATA (CRITICAL)
            # ---------------------------------------
            metadata_val = e.get("metadata")

            # 🔥 HANDLE ALL INVALID CASES
            if not isinstance(metadata_val, dict):
                e["metadata"] = {}

            # ---------------------------------------
            # NORMAL FLOW (UNCHANGED)
            # ---------------------------------------
            score_data = self._score_element(e)
            flags = self._generate_flags(score_data)

            e["quality_score"] = score_data["score"]
            e["is_manual_review"] = score_data["score"] < 0.70
            e["flag_reason"] = flags

            debug.collect(e, score_data)

            enriched.append(e)

        debug_report = debug.build()

        return enriched, debug_report

    # -------------------------
    # SCORING
    # -------------------------

    def _score_element(self, e):

        metadata = e.get("metadata") or {}

        extraction_mode = metadata.get("extraction_mode", "digital")
        ocr_conf = metadata.get("ocr_confidence")

        # BASE SCORE
        if extraction_mode == "digital":
            score = 1.0
        else:
            score = (ocr_conf or 0) / 100

        penalties = []

        text = e.get("content_original", "")

        # corruption (element-level)
        if self._is_element_corrupted(text):
            score *= 0.5
            penalties.append("corrupted_text")

        # noise
        if is_noise(text, e.get("element_type"), self.noise_patterns):
            score *= 0.7
            penalties.append("noise_detected")

        # low content
        if e.get("token_count", 0) < 3:
            score *= 0.6
            penalties.append("low_content")
        
        # table
        if e.get("element_type") == "table":
            if ocr_conf is not None:
                score = max(score, ocr_conf / 100)

        score = max(min(score, 1.0), 0.0)

        return {
            "score": round(score, 3),
            "penalties": penalties,
            "ocr_conf": ocr_conf
        }

    # -------------------------
    # FLAGS
    # -------------------------

    def _generate_flags(self, score_data):

        flags = []

        if score_data["ocr_conf"] is not None and score_data["ocr_conf"] < 60:
            flags.append("low_ocr_confidence")

        flags.extend(score_data["penalties"])

        return list(set(flags))


# -------------------------
# DEBUG REPORT
# -------------------------

class DebugCollector:

    def __init__(self, document_id):
        self.document_id = document_id
        self.pages = {}

    def collect(self, element, score_data):

        metadata = element.get("metadata") or {}
        page = metadata.get("page_number", "unknown")

        page_data = self.pages.setdefault(page, {
            "elements": 0,
            "flagged": 0,
            "flags": [],
            "ocr_conf": score_data["ocr_conf"],
            "issues": []   
        })

        page_data["elements"] += 1

        if score_data["score"] < 0.70:
            page_data["flagged"] += 1
            page_data["flags"].extend(score_data["penalties"])

            # ✅ ADD DETAILED ISSUE
            page_data["issues"].append({
                "element_id": element.get("element_id"),
                "sequence_order": element.get("sequence_order"),
                "page_number": page,
                "quality_score": score_data["score"], 
                "element_type": element.get("element_type"),
                "reason": score_data["penalties"],
                "token_count": element.get("token_count"),
                "text_preview": (element.get("content_original", "")[:120])
            })
            
    def build(self):

        # remove duplicate flags per page
        for page_data in self.pages.values():
            page_data["flags"] = list(set(page_data["flags"]))

        return {
            "document_id": self.document_id,
            "pages": self.pages
        }