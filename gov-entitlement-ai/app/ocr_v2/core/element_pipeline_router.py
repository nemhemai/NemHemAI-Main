# app/ocr_v2/core/element_pipeline_router.py

import logging

from typing import Dict, Any

from app.ocr_v2.cleanup.normalization import (
    canonicalize_unicode
)

from app.ocr_v2.cleanup.script_cleanup import (
    remove_mixed_script_noise
)

from app.ocr_v2.cleanup.noise import (
    filter_ocr_noise
)

from app.ocr_v2.cleanup.table_cleanup import clean_table_text


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


# ─────────────────────────────────────────────────────────────
# ELEMENT TYPE CONSTANTS
# ─────────────────────────────────────────────────────────────

PARAGRAPH_TYPES = {

    "paragraph",
    "text",
    "section",
}

HEADING_TYPES = {

    "heading",
    "title",
    "header",
    "subheading",
}

CLAUSE_TYPES = {

    "clause",
    "bullet",
    "list_item",
}

TABLE_TYPES = {

    "table",
}

FOOTNOTE_TYPES = {

    "footnote",
    "footer",
    "page_footer",
}


# ─────────────────────────────────────────────────────────────
# BASE NORMALIZATION PIPELINE
# Shared deterministic preprocessing stage.
# ─────────────────────────────────────────────────────────────

def apply_base_normalization(
    text: str
) -> str:

    """
    Shared preprocessing foundation.

    Responsibilities:
    - unicode canonicalization
    - spacing normalization
    - deterministic OCR cleanup
    """

    text = canonicalize_unicode(text)

    return text


# ─────────────────────────────────────────────────────────────
# PARAGRAPH PIPELINE
# Most aggressive safe cleanup pipeline because
# paragraphs contain the largest OCR corruption volume.
# ─────────────────────────────────────────────────────────────

def process_paragraph(
    text: str
) -> str:

    logger.info(
        "Running paragraph preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    text = remove_mixed_script_noise(text)

    text = filter_ocr_noise(text)

    return text


# ─────────────────────────────────────────────────────────────
# HEADING PIPELINE
# Conservative cleanup because headings are short
# and aggressive cleanup may damage semantics.
# ─────────────────────────────────────────────────────────────

def process_heading(
    text: str
) -> str:

    logger.info(
        "Running heading preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    # Avoid aggressive multilingual cleanup
    # on short heading structures.
    text = filter_ocr_noise(text)

    return text


# ─────────────────────────────────────────────────────────────
# CLAUSE PIPELINE
# Ultra-safe cleanup because clauses may contain:
# - legal references
# - structured numbering
# - abbreviated forms
# ─────────────────────────────────────────────────────────────

def process_clause(
    text: str
) -> str:

    logger.info(
        "Running clause preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    # Only lightweight OCR refinement
    text = filter_ocr_noise(text)

    return text


# ─────────────────────────────────────────────────────────────
# TABLE PIPELINE
# Tables require structure-preserving cleanup.
#
# Current version intentionally conservative.
# Future:
# - table_cleanup.py
# - numeric-safe cleanup
# - delimiter-aware cleanup
# - column-preserving cleanup
# ─────────────────────────────────────────────────────────────

def process_table(
    text: str
) -> str:

    logger.info(
        "Running table preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    # Avoid aggressive cleanup until
    # dedicated table_cleanup.py is built.
    text = clean_table_text(text)

    return text


# ─────────────────────────────────────────────────────────────
# FOOTNOTE / METADATA PIPELINE
# Conservative cleanup because metadata regions often
# contain IDs, references, dates, URLs, etc.
# ─────────────────────────────────────────────────────────────

def process_footnote(
    text: str
) -> str:

    logger.info(
        "Running footnote preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    text = filter_ocr_noise(text)

    return text


# ─────────────────────────────────────────────────────────────
# DEFAULT FALLBACK PIPELINE
# Safe fallback for unknown element types.
# ─────────────────────────────────────────────────────────────

def process_default(
    text: str
) -> str:

    logger.info(
        "Running default preprocessing pipeline"
    )

    text = apply_base_normalization(text)

    text = filter_ocr_noise(text)

    return text


# ─────────────────────────────────────────────────────────────
# MAIN ELEMENT ROUTER
# ─────────────────────────────────────────────────────────────

def route_element_processing(
    element: Dict[str, Any]
) -> Dict[str, Any]:

    """
    Route OCR preprocessing dynamically based on
    element type.

    This acts as the orchestration layer for:
    - element-aware preprocessing
    - future OCR confidence routing
    - future semantic repair routing
    - future table-aware processing

    Input:
        {
            "element_type": "...",
            "content_original": "..."
        }

    Output:
        original element +
        processed content
    """

    if not element:

        return element

    element_type = (
        element.get("element_type", "")
        .strip()
        .lower()
    )

    text = element.get(
        "content_original",
        ""
    )

    if not text:

        return element

    logger.info(
        f"Routing preprocessing for element type: "
        f"{element_type}"
    )

    # --------------------------------------------------------
    # PARAGRAPH PIPELINE
    # --------------------------------------------------------

    if element_type in PARAGRAPH_TYPES:

        cleaned_text = process_paragraph(text)

    # --------------------------------------------------------
    # HEADING PIPELINE
    # --------------------------------------------------------

    elif element_type in HEADING_TYPES:

        cleaned_text = process_heading(text)

    # --------------------------------------------------------
    # CLAUSE PIPELINE
    # --------------------------------------------------------

    elif element_type in CLAUSE_TYPES:

        cleaned_text = process_clause(text)

    # --------------------------------------------------------
    # TABLE PIPELINE
    # --------------------------------------------------------

    elif element_type in TABLE_TYPES:

        cleaned_text = process_table(text)

    # --------------------------------------------------------
    # FOOTNOTE PIPELINE
    # --------------------------------------------------------

    elif element_type in FOOTNOTE_TYPES:

        cleaned_text = process_footnote(text)

    # --------------------------------------------------------
    # DEFAULT FALLBACK
    # --------------------------------------------------------

    else:

        cleaned_text = process_default(text)

    # --------------------------------------------------------
    # RETURN ENRICHED ELEMENT
    # --------------------------------------------------------

    enriched_element = dict(element)

    enriched_element["content_cleaned"] = cleaned_text

    enriched_element["preprocessing_pipeline"] = element_type

    return enriched_element