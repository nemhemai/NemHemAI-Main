# app/ocr_v2/core/language_router.py

import logging

from typing import Dict

from app.ocr_v2.languages.gujarati.patterns import (
    GUJARATI_OCR_REPAIR_MAP
)

from app.ocr_v2.shared.indic_patterns import (
    SHARED_INDIC_REPAIR_MAP
)


# ─────────────────────────────────────────────────────────────
# LOGGER CONFIGURATION
# ─────────────────────────────────────────────────────────────

logger = logging.getLogger("ocr_pipeline_v2")

if not logger.handlers:

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [OCRv2] %(message)s"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)

logger.setLevel(logging.INFO)


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {

    "gujarati",

    "hindi",

    "marathi",

    "english",
}


# ============================================================
# LANGUAGE DETECTION
#
# Current implementation:
# - conservative
# - Gujarati-first
# - production-safe
#
# Future:
# - probabilistic detection
# - multilingual dominance analysis
# - OCR confidence routing
# ============================================================

def detect_primary_language(
    text: str
) -> str:

    """
    Detect dominant OCR language.

    Current strategy:
    - Gujarati-first fallback
    - lightweight script inspection

    Future:
    - multilingual statistical routing
    """

    if not text:

        return "gujarati"

    gujarati_chars = sum(

        1

        for ch in text

        if '\u0A80' <= ch <= '\u0AFF'
    )

    devanagari_chars = sum(

        1

        for ch in text

        if '\u0900' <= ch <= '\u097F'
    )

    latin_chars = sum(

        1

        for ch in text

        if (
            'A' <= ch <= 'Z'
            or
            'a' <= ch <= 'z'
        )
    )

    # --------------------------------------------------------
    # Gujarati dominant
    # --------------------------------------------------------

    if gujarati_chars >= max(
        devanagari_chars,
        latin_chars
    ):

        return "gujarati"

    # --------------------------------------------------------
    # Hindi / Marathi placeholder
    # --------------------------------------------------------

    if devanagari_chars > latin_chars:

        return "hindi"

    # --------------------------------------------------------
    # English fallback
    # --------------------------------------------------------

    return "english"


# ============================================================
# LANGUAGE REPAIR MAP LOADER
# ============================================================

def get_language_repair_map(
    language: str
) -> Dict[str, str]:

    """
    Load language-specific OCR repair map.

    Current implementation:
    - Gujarati fully supported
    - shared Indic repairs merged

    Future:
    - Hindi repair maps
    - Marathi repair maps
    - English repair maps
    """

    language = (
        language
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Gujarati
    # --------------------------------------------------------

    if language == "gujarati":

        merged = {}

        merged.update(
            SHARED_INDIC_REPAIR_MAP
        )

        merged.update(
            GUJARATI_OCR_REPAIR_MAP
        )

        return merged

    # --------------------------------------------------------
    # Hindi placeholder
    # --------------------------------------------------------

    if language == "hindi":

        return dict(
            SHARED_INDIC_REPAIR_MAP
        )

    # --------------------------------------------------------
    # Marathi placeholder
    # --------------------------------------------------------

    if language == "marathi":

        return dict(
            SHARED_INDIC_REPAIR_MAP
        )

    # --------------------------------------------------------
    # English placeholder
    # --------------------------------------------------------

    if language == "english":

        return dict(
            SHARED_INDIC_REPAIR_MAP
        )

    # --------------------------------------------------------
    # Safe fallback
    # --------------------------------------------------------

    logger.warning(
        f"Unsupported language detected: {language}"
    )

    return dict(
        SHARED_INDIC_REPAIR_MAP
    )


# ============================================================
# FULL LANGUAGE ROUTING
# ============================================================

def route_language_processing(
    text: str
) -> Dict:

    """
    Central language orchestration layer.

    Returns:
        {
            "language": "...",
            "repair_map": {...}
        }

    Future:
    - OCR confidence routing
    - multilingual segmentation
    - hybrid repair orchestration
    """

    language = detect_primary_language(
        text
    )

    repair_map = get_language_repair_map(
        language
    )

    logger.info(
        f"Language routed: {language}"
    )

    return {

        "language": language,

        "repair_map": repair_map,
    }