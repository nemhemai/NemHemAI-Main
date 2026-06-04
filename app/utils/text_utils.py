# app/utils/text_utils.py

"""
text_utils.py
────────────────────────────────────────────────────────────
Utilities for language detection, text normalization,
and token estimation used in PDF extraction pipelines.
"""

import re
from collections import Counter
import unicodedata

def _clean_gujarati_ocr_noise(text: str) -> str:
    """
    Targeted cleanup based on real OCR patterns observed.
    Conservative: removes only confirmed garbage.
    """

    if not text:
        return text

    # --- 1. Remove phantom UTF-8 garbage ---
    text = re.sub(r"[]", "", text)

    # --- 2. Normalize corrupted Gujarati glyphs ---
    char_map = {
        "ƣ": "લ",
        "ƨ": "સ",
        "Ȣ": "ક",
        "Ȥ": "ગ",
    }

    for bad, good in char_map.items():
        if bad in text:
            text = text.replace(bad, good)

    # --- 3. Remove weird mixed tokens like O°F, ORF ---
    text = re.sub(r"\b[A-Z]*[°£%]+[A-Z]*\b", "", text)

    return text

LANG_MARKERS = {
    "mr": {"आहे", "नाही", "आणि", "महाराष्ट्र", "शासन"},
    "hi": {"भारत", "सरकार", "विभाग", "अधिनियम"},
    "gu": {"ગુજરાત", "સરકાર", "જિલ્લો", "વ્યવસ્થાપન"},
}

SCRIPT_PATTERNS = {
    "gu": r"[\u0A80-\u0AFF]",
    "deva": r"[\u0900-\u097F]",
    "ta": r"[\u0B80-\u0BFF]",
    "te": r"[\u0C00-\u0C7F]",
    "kn": r"[\u0C80-\u0CFF]",
}

# ─────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────

def detect_language(text: str) -> str:

    if not text or not text.strip():
        return "unknown"

    scores = Counter()

    # Script scoring
    for lang, pattern in SCRIPT_PATTERNS.items():
        matches = re.findall(pattern, text)
        scores[lang] += len(matches)

    # Gujarati direct
    if scores["gu"] > 0:
        return "gu"

    # Devanagari refinement
    if scores["deva"] > 0:

        words = set(text.split())

        mr_score = len(words & LANG_MARKERS["mr"])
        hi_score = len(words & LANG_MARKERS["hi"])

        if mr_score > hi_score:
            return "mr"

        return "hi"

    if scores["ta"] > 0:
        return "ta"

    if scores["te"] > 0:
        return "te"

    if scores["kn"] > 0:
        return "kn"

    return "unknown"


# ─────────────────────────────────────────────────────────
# TEXT NORMALIZATION
# ─────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Clean OCR and layout artifacts while preserving meaning.
    """

    text = unicodedata.normalize("NFC", text)

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    text = re.sub(r"\s+([,।;:])", r"\1", text)

    text = re.sub(r"\n+", " ", text)

    return text.strip()


# ─────────────────────────────────────────────────────────
# TOKEN ESTIMATION
# ─────────────────────────────────────────────────────────

def count_tokens(text: str, lang: str = "en") -> int:
    """
    Estimate token count for chunking and embedding.
    """

    # Indic scripts tend to have fewer spaces
    if lang in ("hi", "mr", "ta", "te", "kn", "gu"):
        return max(1, len(text) // 4)

    return len(text.split())

def detect_section_label(text, element_type):
    """
    Detect section headings in government documents.
    """

    if element_type == "table":
        return None

    text = text.strip()

    if len(text) < 4:
        return None

    if re.search(r"[^\w\s\.\)\(\-]", text) and len(text) < 8:
        return None

    if len(text) > 120:
        return None

    blocklist = re.compile(
        r"(notification\s*no|date\s*:|ref\s*no|sl\s*no)",
        re.IGNORECASE
    )

    if blocklist.search(text):
        return None

    if re.fullmatch(r"\d{4,}", text):
        return None

    # Numeric sections
    numeric_match = re.match(r"^\d{1,3}(\.\d{1,3})*[\.)]?", text)

    if numeric_match:
        label = numeric_match.group(0).rstrip(")")
        return label

    # English headings
    keyword_pattern = re.compile(
        r"^(chapter|section|rule|clause|schedule|appendix|annexure|part)"
        r"[\s\.\-]+"
        r"([IVXLCDM]{1,6}|\d+(\.\d+)*|[A-Z])",
        re.IGNORECASE
    )

    if keyword_pattern.match(text):
        return text[:60]

    # Devanagari headings
    deva_pattern = re.compile(
        r"^(अध्याय|धारा|अनुच्छेद|नियम|खण्ड|अनुसूची|भाग)"
        r"[\s\u0964\u0965]*(\d+|[०-९]+)?"
    )

    if deva_pattern.match(text):
        return text[:60]

    # ALL CAPS headings
    s = text.strip()

    if s.isupper() and 4 < len(s) < 80 and " " in s:
        if not re.search(r"[_]{2,}", s):
            return s[:60]

    return None


def is_valid_section_label(label, original_text=None):
    """
    Validate detected section labels and reject OCR artifacts.
    """

    label = label.strip()

    # Reject obvious symbol noise
    if re.search(r"[\/><_]{2,}", label):
        return False

    # Reject very long numbers
    if re.fullmatch(r"\d{3,}", label):
        return False

    # Reject reference number patterns like 16/2018
    if re.search(r"\d+/\d+", label):
        return False

    # Reject mixed scripts (OCR garbage)
    if re.search(r"[A-Za-z].*[अ-ह]|[अ-ह].*[A-Za-z]", label):
        return False

    # Reject mostly numeric punctuation
    if re.fullmatch(r"[\d\.\-\)\(]+", label) and len(label) > 4:
        return False

    if len(label) < 2:
        return False

    # Extra check on original text
    if original_text:

        t = original_text.lower()

        # Reject notification numbers / file numbers
        if re.search(r"\d+/\d{3,}", t):
            return False

        if re.search(r"(ref|no\.|notification|swma|iec)", t):
            return False

    return True

# ─────────────────────────────────────────────────────────────
# CLAUSE NORMALIZATION
# ─────────────────────────────────────────────────────────────

def normalize_clause_text(text):
    """
    Clean OCR artifacts and numbering noise in clause text.
    """

    if not text:
        return text

    t = text.strip()

    # Remove duplicated clause numbers like "3) 3)"
    t = re.sub(r'^(\d+\)\s*){2,}', '', t)

    # Remove nested numbering patterns like "29) 3)"
    t = re.sub(r'^\d+\)\s*\d+\)\s*', '', t)

    # Remove single leading numbering like "3)"
    t = re.sub(r'^\d+\)\s*', '', t)

    # Remove bullet patterns
    t = re.sub(r'^[•\-–]+\s*', '', t)

    # Remove pipe artifacts
    t = re.sub(r'\|+', ' ', t)

    # Remove repeated punctuation artifacts
    t = re.sub(r'[_]{2,}', ' ', t)

    # Fix spacing
    t = re.sub(r'\s+', ' ', t)

    return t.strip()


# ─────────────────────────────────────────────────────────────
# OCR ERROR CORRECTION (UPDATED PIPELINE)
# ─────────────────────────────────────────────────────────────

DOMAIN_WORDS = {
    "government", "municipal", "municipality", "corporation",
    "management", "biodegradable", "composting", "segregation",
    "transportation", "sanitation", "cleanliness",
    "byelaws", "schedule", "annexure", "appendix",
    "maharashtra", "brihanmumbai"
}

OCR_WORD_CORRECTIONS = {
    "goverrnment": "government",
    "managment": "management",
    "managgement": "management",
    "corpporation": "corporation",
    "municipallity": "municipality",
    "committtee": "committee",
    "sectiion": "section",
    "notificaation": "notification",
    "authorizaation": "authorization",
    "departmennt": "department",
    "implementaation": "implementation",
    "byelawws": "byelaws",
    "schedulle": "schedule",
    "penallty": "penalty",
    "violaation": "violation",
    "compliiance": "compliance",
    "segregaation": "segregation",
    "waaste": "waste",
    "soliid": "solid",
}

MARATHI_HINDI_CORRECTIONS = {
    "धचनकचरा": "घनकचरा",
    "घनकचरराा": "घनकचरा",
    "कचरराा": "कचरा",
    "त्यावस्थापना": "व्यवस्थापन",
    "व्ययवस्थापन": "व्यवस्थापन",
    "व्यवस्थापनन": "व्यवस्थापन",
    "किवा": "किंवा",
    "कीवा": "किंवा",
    "किींवा": "किंवा",
    "ळाख": "लाख",
    "लाःख": "लाख",
    "fear": "किंवा",
    "R025": "2016"
}
GUJARATI_OCR_CORRECTIONS = {

    # ─────────────────────────────────────────
    # COMMON GOVERNMENT WORDS
    # ─────────────────────────────────────────
    
    # --- From your actual OCR samples ---
    "સાંƨ Ȣૃિતક": "સાંસ્કૃતિક",
    "ભૌગોલક": "ભૌગોલિક",
    "જƣલો": "જિલ્લો",

    # After cleanup fallback (safety)
    "સાં સ્કૃતિક": "સાંસ્કૃતિક",
    "ભૌગો લિક": "ભૌગોલિક",
    "જિલલો": "જિલ્લો",
    
    
    "સરકર": "સરકાર",
    "સરકારશ્રીનાા": "સરકારશ્રીના",
    "સરકાર શ્રી": "સરકારશ્રી",

    "અધિનિયમ્": "અધિનિયમ",
    "અધિનિયમમ": "અધિનિયમ",

    "નોટીફિકેશન": "નોટિફિકેશન",
    "નોટીફેકેશન": "નોટિફિકેશન",
    "નોટીફિકેશાન": "નોટિફિકેશન",

    "વિભાગ્": "વિભાગ",
    "વિભાગા": "વિભાગ",

    "ઠરાવ્": "ઠરાવ",
    "ઠરાવા": "ઠરાવ",

    "પત્ર્": "પત્ર",
    "પત્રા": "પત્ર",

    "યોજનાનાા": "યોજનાના",

    "મહાનગરપાલિકાા": "મહાનગરપાલિકા",
    "મહાનગર પાલિકા": "મહાનગરપાલિકા",

    "નગરપાલિકાા": "નગરપાલિકા",

    "વ્યવસ્થાાપન": "વ્યવસ્થાપન",
    "વ્યવસ્થાપનન": "વ્યવસ્થાપન",

    "કચરરો": "કચરો",
    "કચરરા": "કચરા",

    "પરવાનગીિ": "પરવાનગી",

    "નિયમોો": "નિયમો",

    # ─────────────────────────────────────────
    # GOVERNMENT FORMAT / ABBREVIATIONS
    # ─────────────────────────────────────────
    "કઃ": "ક્ર.",
    "કઃ૦": "ક્ર.0",
    "કઃનઅપ": "ક્ર. નં.",
    "કઃનં": "ક્ર. નં.",
    "કઃઆર": "ક્ર.આર.",

    "ક્ર નં": "ક્ર. નં.",
    "ક્ર નં.": "ક્ર. નં.",
    "ક્ર.નં": "ક્ર. નં.",

    # ─────────────────────────────────────────
    # NUMBER / YEAR CORRECTION
    # ─────────────────────────────────────────
    "૧૦૨૦૧૩": "૨૦૧૩",
    "૧૦૨૦૧૪": "૨૦૧૪",
    "૧૦૨૦૧૫": "૨૦૧૫",
    "૧૦૨૦૧૬": "૨૦૧૬",
    "૧૦૨૦૧૭": "૨૦૧૭",
    "૧૦૨૦૧૮": "૨૦૧૮",

    "૧ £": "૧",

    # ─────────────────────────────────────────
    # MIXED SCRIPT (CRITICAL)
    # ─────────────────────────────────────────
    "सीटीऊन्स": "સિટિઝન્સ",
    "अधिनियम": "અધિનિયમ",
    "नगरपालिका": "નગરપાલિકા",

    # ─────────────────────────────────────────
    # SYMBOL / OCR NOISE
    # ─────────────────────────────────────────
    "£": "",
    "||": " ",
    "॥": " ",
    "।।": " ",
    "—": "-",

    # ─────────────────────────────────────────
    # SPLIT WORD FIXES
    # ─────────────────────────────────────────
    "મ. વિ.": "મ.વિ.",
    "સા. વ. વિ.": "સા.વ.વિ.",
    "પ્ર. મ.": "પ્ર.મ.",
    
    # --- Common OCR glyph corruption ---
    "ƣ": "લ",
    "ƨ": "સ",
    "Ȣ": "ક",
    "Ȥ": "ગ",

    # --- Broken conjunct fixes ---
    "ƨ થ": "સ્થ",
    "સ થ": "સ્થ",
    "ƨથ": "સ્થ",

    # --- High-frequency real corrections ---
    "જƣલો": "જિલ્લો",
    "સાંƨ Ȣૃિતક": "સાંસ્કૃતિક",
    "ભૌગોલક": "ભૌગોલિક",
    "Ȥુજરાત": "ગુજરાત",

    # --- Remove obvious junk tokens ---
    "": "",
    "": "",
}


def _fix_triple_plus_chars(text: str) -> str:
    """
    Reduce runs of 3+ identical characters to 2.
    """
    return re.sub(r"(.)\1{2,}", r"\1\1", text)


def _apply_word_dict(word: str) -> str:
    """
    Apply word-level OCR correction dictionary.
    """

    lower = word.lower()

    if lower not in OCR_WORD_CORRECTIONS:
        return word

    correct = OCR_WORD_CORRECTIONS[lower]

    if word.isupper():
        return correct.upper()

    if word[0].isupper():
        return correct.capitalize()

    return correct


def _merge_word_splits(tokens):
    """
    Merge split words based on DOMAIN_WORDS.
    """

    merged = []
    i = 0

    while i < len(tokens):

        if i + 1 < len(tokens):

            w1 = tokens[i]
            w2 = tokens[i + 1]

            combined = (w1 + w2).lower()

            if combined in DOMAIN_WORDS and len(w1) >= 3 and len(w2) >= 2:

                if w1[0].isupper():
                    combined = combined.capitalize()

                merged.append(combined)
                i += 2
                continue

        merged.append(tokens[i])
        i += 1

    return merged

def normalize_gujarati_numbers(text: str) -> str:
    """
    Fix Gujarati number OCR errors.
    'ર૦' is a common OCR misread of '૨૦' (the digit 2 misread as 'ર').
    Applied after year-specific corrections in GUJARATI_OCR_CORRECTIONS
    so longer patterns like '૧૦૨૦૧૩' are already fixed before this runs.
    """
    # 'ર' misread as '૨' — only at word boundary to avoid corrupting real words
    text = re.sub(r'\bર૦', '૨૦', text)
    return text

# Single Hindi function words that appear as noise in Gujarati documents
# Matched at word boundaries to avoid corrupting mid-word substrings
_HINDI_NOISE_PATTERN = re.compile(r'\b(न|है|के)\b')


def correct_ocr_errors(text: str) -> str:
    """
    Improved OCR correction pipeline.
    """

    if not text or not text.strip():
        return text
    
    # Phase 0: Gujarati OCR noise cleanup
    text = _clean_gujarati_ocr_noise(text)

    # Phase 1: Marathi/Hindi corrections (substring replacement — safe for known errors)
    for wrong, correct in MARATHI_HINDI_CORRECTIONS.items():
        if wrong in text:
            text = text.replace(wrong, correct)

    # Phase 1b: Gujarati corrections
    for wrong, correct in GUJARATI_OCR_CORRECTIONS.items():
        if wrong in text:
            text = text.replace(wrong, correct)
    
    # Phase 1b.1: Fix broken Gujarati conjuncts (observed pattern)
    text = re.sub(r"\bસ\s*થ\b", "સ્થ", text)
    text = re.sub(r"\bસ્\s*થ\b", "સ્થ", text)

    # Phase 1c: Remove Hindi noise tokens at word boundaries only
    text = _HINDI_NOISE_PATTERN.sub('', text)

    # Phase 1d: Gujarati number normalization
    text = normalize_gujarati_numbers(text)

    # Phase 2: Fix repeated characters (3+ → 2)
    text = _fix_triple_plus_chars(text)

    # Phase 3: Word dictionary corrections (English)
    tokens = text.split()
    tokens = [_apply_word_dict(t) for t in tokens]

    # Phase 4: Word split merging
    tokens = _merge_word_splits(tokens)

    return " ".join(tokens)

def is_text_corrupted(elements):

    if not elements:
        return True

    total = len(elements)

    glyph_count = 0
    meaningful_text = 0

    for e in elements[:20]:

        text = e.get("content_original", "").strip().lower()

        if not text:
            continue

        if "glyph" in text:
            glyph_count += 1

        # meaningful text check
        if len(text) > 20 and any(c.isalpha() for c in text):
            meaningful_text += 1

    glyph_ratio = glyph_count / total
    meaningful_ratio = meaningful_text / total

    # ✅ FINAL DECISION
    return (
        glyph_ratio > 0.3   # heavy corruption
        or meaningful_ratio < 0.3  # weak extraction
    )
    
    
##################################################################


# ─────────────────────────────────────────────────────────────
# NEW PRODUCTION-GRADE OCR NORMALIZATION PIPELINE (v2, DISABLED)
# ─────────────────────────────────────────────────────────────
"""
This block introduces a forward-compatible, production-grade OCR normalization pipeline
designed for multilingual RAG systems handling Gujarati, Hindi, Marathi, and English.

⚠️ Safety Notes:
    - The existing OCR logic remains intact and unmodified.
    - This block is isolated, wrapped in feature flags, and NOT executed unless explicitly enabled.
    - It may be enabled in future releases via simple flag toggling or with pipeline integration.

Core goals:
    1. Unicode canonicalization
    2. Script detection and segmentation
    3. OCR noise filtering
    4. Character confusion repair
    5. Entity-aware correction scaffolding
    6. Extensible architecture for ByT5 or neural postprocessors
"""

import logging
from typing import List, Dict, Optional
from unicodedata import normalize

# ─────────────────────────────────────────────────────────────
# FEATURE FLAG (DISABLED)
# ─────────────────────────────────────────────────────────────
ENABLE_NEW_OCR_PIPELINE = False  # Set to True later after testing


# ─────────────────────────────────────────────────────────────
# LOGGER CONFIGURATION
# ─────────────────────────────────────────────────────────────
logger = logging.getLogger("ocr_pipeline_v2")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [OCRv2] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ─────────────────────────────────────────────────────────────
# UNICODE CANONICALIZATION
# ─────────────────────────────────────────────────────────────
def canonicalize_unicode(text: str) -> str:
    """
    Normalize text to Unicode NFKC form and remove layout/control artifacts.
    """
    if not text:
        return text

    t = normalize("NFKC", text)
    t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)  # zero-width chars
    t = re.sub(r"[‘’´`]", "'", t)                     # normalize apostrophes
    t = re.sub(r"[“”]", '"', t)                      # normalize quotes
    t = re.sub(r"[‐‑‒–—―]", "-", t)                  # dashes
    t = re.sub(r"\s+", " ", t).strip()               # spaces
    return t


# ─────────────────────────────────────────────────────────────
# SCRIPT DETECTION & SEGMENTATION
# ─────────────────────────────────────────────────────────────
SCRIPT_RANGES = {
    "gu": (0x0A80, 0x0AFF),
    "hi": (0x0900, 0x097F),
    "mr": (0x0900, 0x097F),
    "en": (0x0000, 0x007F),
}

OTHER_INDIC_SCRIPTS = [

    # Bengali
    (0x0980, 0x09FF),

    # Oriya
    (0x0B00, 0x0B7F),

    # Tamil
    (0x0B80, 0x0BFF),

    # Telugu
    (0x0C00, 0x0C7F),

    # Kannada
    (0x0C80, 0x0CFF),

    # Malayalam
    (0x0D00, 0x0D7F),
]

def detect_script(ch: str) -> Optional[str]:
    """
    Identify approximate script of a given character.
    """
    cp = ord(ch)
    for lang, (start, end) in SCRIPT_RANGES.items():
        if start <= cp <= end:
            return lang
    return None


def remove_mixed_script_noise(text: str) -> str:
    """
    Remove meaningless character intrusions from unrelated scripts
    (example: stray Kannada glyphs in Gujarati).
    """
    cleaned = []
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in OTHER_INDIC_SCRIPTS):
            continue  # drop noise
        cleaned.append(ch)
    return "".join(cleaned)


# ─────────────────────────────────────────────────────────────
# OCR NOISE FILTERING
# ─────────────────────────────────────────────────────────────
NOISE_PATTERN = re.compile(
    r"\b(?:[A-Za-z]{1,3}\d{1,3}[^\w\s]*|[xXqQzZ]{3,}|[A-Z]+[°£$@#]+[A-Z]*)\b"
)


def filter_ocr_noise(text: str) -> str:
    """
    Remove garbage tokens and normalize punctuation.
    """
    text = re.sub(NOISE_PATTERN, "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────
# INDIC CHARACTER CONFUSION REPAIR
# ─────────────────────────────────────────────────────────────
INDIC_CONFUSION_MAP = {
    # Gujarati confusions
    "ર૦": "૨૦",  # common OCR confusion for "20"
    #"થ": "સ્થ",  # when context-misaligned
    # Hindi/Marathi matra issues (example placeholders)
    "किीं": "किं",
    "कीवा": "किंवा",
}


def repair_indic_confusions(text: str) -> str:
    """
    Conservative repair of common Indic OCR confusions.
    """
    for wrong, correct in INDIC_CONFUSION_MAP.items():
        if wrong in text:
            text = text.replace(wrong, correct)
    return text


# ─────────────────────────────────────────────────────────────
# ENTITY-AWARE REPAIR PIPELINE (PLACEHOLDER)
# ─────────────────────────────────────────────────────────────
class EntityDictionary:
    """
    Holds domain-specific entities and supports fuzzy correction.
    Future integration: RapidFuzz/Levenshtein for distance matching.
    """
    def __init__(self, entities: Optional[List[str]] = None):
        self.entities = set(e.lower() for e in (entities or []))

    def suggest(self, token: str) -> Optional[str]:
        # Placeholder logic: return exact match or None
        low = token.lower()
        if low in self.entities:
            return token
        return None


# ─────────────────────────────────────────────────────────────
# FUTURE CONTEXTUAL REPAIR ARCHITECTURE (ByT5 HOOKS)
# ─────────────────────────────────────────────────────────────
class NeuralRepairInterface:
    """
    Placeholder for future neural OCR correction model (ByT5 or similar).
    This interface will handle contextual restoration in future versions.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def repair(self, text: str) -> str:
        logger.debug("Neural repair placeholder invoked.")
        return text  # Placeholder — actual inference not yet implemented


# ─────────────────────────────────────────────────────────────
# MASTER PIPELINE (V2 ENTRY POINT – DISABLED)
# ─────────────────────────────────────────────────────────────
def correct_ocr_errors_v2(
    text: str,
    lang_hint: Optional[str] = None,
    entity_dict: Optional[EntityDictionary] = None
) -> str:
    """
    Next-generation OCR correction pipeline (non-executing wrapper).
    """

    if not ENABLE_NEW_OCR_PIPELINE:
        logger.debug("New OCR pipeline skipped (feature flag disabled).")
        return text  # bypass existing flow safely

    try:
        logger.info("Starting OCR correction v2...")
        text = canonicalize_unicode(text)
        text = remove_mixed_script_noise(text)
        text = filter_ocr_noise(text)
        text = repair_indic_confusions(text)

        if entity_dict:
            tokens = text.split()
            text = " ".join(
                entity_dict.suggest(tok) or tok for tok in tokens
            )

        # Placeholder neural repair (no inference yet)
        neural = NeuralRepairInterface()
        text = neural.repair(text)

    except Exception as exc:
        logger.error(f"OCRv2 pipeline failed: {exc}")
        # Fail-safe fallback to original text
        return text

    return text


# ─────────────────────────────────────────────────────────────
# SAFE ACTIVATION PLAN
# ─────────────────────────────────────────────────────────────
"""
To activate the new OCR pipeline:

1. Flip the feature flag at the top:
       ENABLE_NEW_OCR_PIPELINE = True

2. Update pipeline integration site (e.g., inside `correct_ocr_errors` or
   document preprocessing flow):

       text = correct_ocr_errors_v2(text, lang_hint=detect_language(text))

3. Monitor logs under logger name `ocr_pipeline_v2` to trace normalization behavior.

Rollback is instant — set the flag back to False.
No existing functions are modified or replaced.
"""
