# app/ocr_v2/classification/corruption_classifier.py

import re

from typing import Dict

from app.ocr_v2.patterns import (

    BROKEN_GLYPH_PATTERN,

    CORRUPTED_NUMERIC_PATTERN,

    SYMBOL_GARBAGE_PATTERN,

    MULTILINGUAL_TOKEN_PATTERN,

    SUSPICIOUS_LATIN_FRAGMENT_PATTERN,

    TAMIL_SCRIPT_PATTERN,

    TELUGU_SCRIPT_PATTERN,

    KANNADA_SCRIPT_PATTERN,

    BENGALI_SCRIPT_PATTERN,
)


# ─────────────────────────────────────────────────────────────
# GUJARATI RANGE
# ─────────────────────────────────────────────────────────────

GUJARATI_RANGE = (
    "\u0A80",
    "\u0AFF"
)


# ─────────────────────────────────────────────────────────────
# KNOWN OCR HALLUCINATION TOKENS
# ─────────────────────────────────────────────────────────────

KNOWN_OCR_HALLUCINATIONS = {

    "rissa",
    "als",
    "anal",
    "ofiicer",
    "orf",
    "uhl",
    "uh",
    "aht",
    "mga",
    "phere",
    "seq",
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def contains_gujarati(token: str) -> bool:

    return any(

        '\u0A80' <= ch <= '\u0AFF'

        for ch in token
    )


def contains_foreign_script(token: str) -> bool:

    patterns = [

        TAMIL_SCRIPT_PATTERN,

        TELUGU_SCRIPT_PATTERN,

        KANNADA_SCRIPT_PATTERN,

        BENGALI_SCRIPT_PATTERN,
    ]

    return any(
        p.search(token)
        for p in patterns
    )


def contains_multiple_numeric_systems(
    token: str
) -> bool:

    numeral_systems = set()

    for ch in token:

        cp = ord(ch)

        # ASCII numerals
        if '0' <= ch <= '9':
            numeral_systems.add("ascii")

        # Gujarati numerals
        elif 0x0AE6 <= cp <= 0x0AEF:
            numeral_systems.add("gujarati")

        # Devanagari numerals
        elif 0x0966 <= cp <= 0x096F:
            numeral_systems.add("devanagari")

        # Bengali numerals
        elif 0x09E6 <= cp <= 0x09EF:
            numeral_systems.add("bengali")

        # Kannada numerals
        elif 0x0CE6 <= cp <= 0x0CEF:
            numeral_systems.add("kannada")

        # Tamil numerals
        elif 0x0BE6 <= cp <= 0x0BEF:
            numeral_systems.add("tamil")

    return len(numeral_systems) > 1


def is_ocr_hallucinated_latin(
    token: str
) -> bool:

    token_lower = token.lower()

    # Explicit hallucination vocabulary
    if token_lower in KNOWN_OCR_HALLUCINATIONS:
        return True

    # Suspicious OCR-style character combinations
    suspicious_patterns = [

        r"ii",
        r"vv",
        r"rn",
        r"cl",
        r"[0-9][A-Za-z]",
        r"[A-Za-z][0-9]",
        r"[qxz]{2,}",
    ]

    for pattern in suspicious_patterns:

        if re.search(pattern, token_lower):
            return True

    # Very short uppercase fragments
    if token.isupper() and len(token) <= 3:
        return True

    # Vowelless unnatural fragments
    if token.isalpha():

        vowels = sum(
            1 for ch in token_lower
            if ch in "aeiou"
        )

        if vowels == 0 and len(token) > 3:
            return True

    return False


# ─────────────────────────────────────────────────────────────
# MAIN CLASSIFIER
# ─────────────────────────────────────────────────────────────

def classify_token_corruption(
    token: str
) -> Dict:

    token = token.strip()

    result = {

        "token": token,

        "corruption_type": "clean",

        "repair_strategy": None,

        "repairable": False,

        "llm_candidate": False,
    }

    if not token:

        return result

    # --------------------------------------------------------
    # BROKEN GLYPHS
    # --------------------------------------------------------

    if BROKEN_GLYPH_PATTERN.search(token):

        result.update({

            "corruption_type": "broken_glyph",

            "repair_strategy": "deterministic_cleanup",

            "repairable": True,
        })

        return result

    # --------------------------------------------------------
    # MIXED NUMERAL SYSTEM CORRUPTION
    # --------------------------------------------------------

    if contains_multiple_numeric_systems(token):

        result.update({

            "corruption_type": "mixed_numeral_system_corruption",

            "repair_strategy": "normalize_numerals",

            "repairable": True,
        })

        return result

    # --------------------------------------------------------
    # CORRUPTED NUMERICS
    # --------------------------------------------------------

    if CORRUPTED_NUMERIC_PATTERN.search(token):

        result.update({

            "corruption_type": "corrupted_numeric",

            "repair_strategy": "remove_or_normalize",

            "repairable": True,
        })

        return result

    # --------------------------------------------------------
    # SYMBOL GARBAGE
    # --------------------------------------------------------

    if SYMBOL_GARBAGE_PATTERN.search(token):

        result.update({

            "corruption_type": "symbol_garbage",

            "repair_strategy": "remove",

            "repairable": True,
        })

        return result

    # --------------------------------------------------------
    # SUSPICIOUS LATIN FRAGMENTS
    # --------------------------------------------------------

    if (
        SUSPICIOUS_LATIN_FRAGMENT_PATTERN.search(token)
        and is_ocr_hallucinated_latin(token)
    ):

        result.update({

            "corruption_type": "suspicious_latin_fragment",

            "repair_strategy": "semantic_review",

            "repairable": False,

            "llm_candidate": True,
        })

        return result

    # --------------------------------------------------------
    # MULTILINGUAL SEMANTIC TOKENS
    # --------------------------------------------------------

    if MULTILINGUAL_TOKEN_PATTERN.search(token):

        if contains_gujarati(token):

            result.update({

                "corruption_type": "semantic_multilingual_corruption",

                "repair_strategy": "llm_semantic_reconstruction",

                "repairable": True,

                "llm_candidate": True,
            })

        else:

            result.update({

                "corruption_type": "foreign_multilingual_noise",

                "repair_strategy": "remove",

                "repairable": True,
            })

        return result

    # --------------------------------------------------------
    # FOREIGN SCRIPT LEAKAGE
    # --------------------------------------------------------

    if contains_foreign_script(token):

        if contains_gujarati(token):

            result.update({

                "corruption_type": "mixed_script_semantic_fragment",

                "repair_strategy": "llm_semantic_reconstruction",

                "repairable": True,

                "llm_candidate": True,
            })

        else:

            result.update({

                "corruption_type": "isolated_script_leakage",

                "repair_strategy": "remove",

                "repairable": True,
            })

        return result

    return result