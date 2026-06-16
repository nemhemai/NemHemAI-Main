# app/ocr_v2/patterns.py

import re

# ============================================================
# FOREIGN SCRIPT DETECTION
# ============================================================

TAMIL_SCRIPT_PATTERN = re.compile(
    r"[\u0B80-\u0BFF]"
)

TELUGU_SCRIPT_PATTERN = re.compile(
    r"[\u0C00-\u0C7F]"
)

KANNADA_SCRIPT_PATTERN = re.compile(
    r"[\u0C80-\u0CFF]"
)

BENGALI_SCRIPT_PATTERN = re.compile(
    r"[\u0980-\u09FF]"
)


# ============================================================
# MULTILINGUAL TOKEN DETECTION
# ============================================================

MULTILINGUAL_TOKEN_PATTERN = re.compile(

    r"""
    (
        [\u0900-\u097F].*[\u0A80-\u0AFF]
    )
    |
    (
        [\u0A80-\u0AFF].*[\u0900-\u097F]
    )
    |
    (
        [\u0A80-\u0AFF].*[\u0980-\u09FF]
    )
    |
    (
        [\u0A80-\u0AFF].*[\u0B80-\u0BFF]
    )
    |
    (
        [\u0A80-\u0AFF].*[\u0C00-\u0CFF]
    )
    """,

    re.VERBOSE
)


# ============================================================
# SUSPICIOUS LATIN FRAGMENTS
# ============================================================

SUSPICIOUS_LATIN_FRAGMENT_PATTERN = re.compile(

    r"""
    ^

    [A-Za-z]{2,8}

    $

    """,

    re.VERBOSE
)


# ============================================================
# SCRIPT RANGES
# ============================================================

SCRIPT_RANGES = {

    "gujarati": (0x0A80, 0x0AFF),

    "devanagari": (0x0900, 0x097F),

    "bengali": (0x0980, 0x09FF),

    "oriya": (0x0B00, 0x0B7F),

    "tamil": (0x0B80, 0x0BFF),

    "telugu": (0x0C00, 0x0C7F),

    "kannada": (0x0C80, 0x0CFF),

    "malayalam": (0x0D00, 0x0D7F),

    "latin": (0x0000, 0x007F),
}


# ============================================================
# FOREIGN SCRIPT GROUPING
# Centralized script taxonomy used across:
# - corruption_classifier.py
# - script_cleanup.py
# - analysis modules
# ============================================================

FOREIGN_SCRIPTS = {

    "bengali",

    "oriya",

    "tamil",

    "telugu",

    "kannada",

    "malayalam",
}


# ============================================================
# NUMERAL SYSTEM RANGES
# Used for:
# - mixed numeral corruption detection
# - numeral normalization
# - multilingual numeric leakage analysis
# ============================================================

NUMERAL_SYSTEM_RANGES = {

    "ascii": (0x0030, 0x0039),

    "gujarati": (0x0AE6, 0x0AEF),

    "devanagari": (0x0966, 0x096F),

    "bengali": (0x09E6, 0x09EF),

    "kannada": (0x0CE6, 0x0CEF),

    "tamil": (0x0BE6, 0x0BEF),
}


# ============================================================
# SAFE STRUCTURAL TOKEN PATTERNS
# These tokens should generally be preserved during
# deterministic cleanup stages.
# ============================================================

URL_PATTERN = re.compile(

    r"""
    https?://
    """,

    re.VERBOSE
)

EMAIL_PATTERN = re.compile(

    r"""
    .+@.+
    """,

    re.VERBOSE
)

PHONE_PATTERN = re.compile(

    r"""
    ^[\d\-\+\(\)\s]{6,}$
    """,

    re.VERBOSE
)

FILE_REF_PATTERN = re.compile(

    r"""
    ^[A-Za-z0-9/_\-.]+$
    """,

    re.VERBOSE
)


# ============================================================
# OCR HALLUCINATION PATTERNS
# Used only for classification/routing.
# NOT for semantic correction.
# ============================================================

OCR_HALLUCINATION_PATTERN = re.compile(

    r"""
    (
        [qxz]{2,}
    )
    |
    (
        ii
    )
    |
    (
        vv
    )
    |
    (
        rn
    )
    |
    (
        cl
    )
    |
    (
        [0-9][A-Za-z]
    )
    |
    (
        [A-Za-z][0-9]
    )
    """,

    re.VERBOSE | re.IGNORECASE
)


# ============================================================
# BROKEN OCR GLYPHS
# ============================================================

BROKEN_GLYPH_MAP = {

    "ƨ": "સ",

    "Ȣ": "ક",

    "Ȥ": "ગ",

    "ƣ": "લ",

    "": "",

    "": "",
}


BROKEN_GLYPH_PATTERN = re.compile(

    r"[ƨȢȤƣ]"
)


# ============================================================
# OCR NUMERIC CORRUPTION
# ============================================================

CORRUPTED_NUMERIC_PATTERN = re.compile(

    r"""
    ^

    (?=.*[£$°%])

    (?=.*[০-৯೦-೯०-९૦-૯0-9])

    [A-Za-z০-৯೦-೯०-९૦-૯0-9£$°%_\-—–.]+

    $

    """,

    re.VERBOSE
)


# ============================================================
# MIXED NUMERAL SYSTEM CORRUPTION
# Example:
#   ૦૨4૩२
#   ೦೩20
# ============================================================

MIXED_NUMERAL_SYSTEM_PATTERN = re.compile(

    r"""
    (
        (?=.*[0-9])
        (?=.*[૦-૯])
    )
    |
    (
        (?=.*[0-9])
        (?=.*[०-९])
    )
    |
    (
        (?=.*[0-9])
        (?=.*[০-৯])
    )
    |
    (
        (?=.*[0-9])
        (?=.*[೦-೯])
    )
    """,

    re.VERBOSE
)


# ============================================================
# OCR SYMBOL GARBAGE
# ============================================================

SYMBOL_GARBAGE_PATTERN = re.compile(

    r"""
    (

        [A-Z]+[°£$&’]+[A-Z0-9.\-—–]*

    )

    |

    (

        [£$°&]{2,}

    )

    """,

    re.VERBOSE
)


# ============================================================
# OCR ARTIFACTS
# ============================================================

OCR_ARTIFACT_PATTERN = re.compile(

    r"""
    ^

    (?:

        [O0][°&’][A-Z0-9]

        |

        [A-Z]{2,}[0-9]{2,}

    )

    """,

    re.VERBOSE
)


# ============================================================
# MULTISCRIPT PUNCTUATION
# ============================================================

MULTISCRIPT_PUNCT_PATTERN = re.compile(

    r"[।॥]",

    re.VERBOSE
)


# ============================================================
# ISOLATED SCRIPT LEAKAGE
# ============================================================

ISOLATED_SCRIPT_LEAKAGE_PATTERN = re.compile(

    r"""
    ^

    [\u0980-\u09FF
     \u0B80-\u0BFF
     \u0C00-\u0C7F
     \u0C80-\u0CFF
     \u0D00-\u0D7F]+

    $

    """,

    re.VERBOSE
)


# ============================================================
# FOREIGN-DOMINANT MULTISCRIPT TOKENS
# Example:
#   ஸ்.PDF
#   ೦೩೨೦-AB
# ============================================================

FOREIGN_DOMINANT_TOKEN_PATTERN = re.compile(

    r"""
    (
        [\u0980-\u0D7F]{2,}.*[A-Za-z0-9]
    )
    |
    (
        [A-Za-z0-9].*[\u0980-\u0D7F]{2,}
    )
    """,

    re.VERBOSE
)


# ============================================================
# INDIC OCR CONFUSION REPAIR
# ============================================================

INDIC_CONFUSION_MAP = {

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
    "R025": "2016",

    # ─────────────────────────────────────────
    # COMMON GOVERNMENT WORDS
    # ─────────────────────────────────────────

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
    "૧૦૨૦૧૫": "២០១૫",
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