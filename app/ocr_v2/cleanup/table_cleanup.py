# app/ocr_v2/cleanup/table_cleanup.py

import logging
import re

from typing import List

from app.ocr_v2.patterns import (

    URL_PATTERN,

    EMAIL_PATTERN,

    PHONE_PATTERN,

    FILE_REF_PATTERN,

    MIXED_NUMERAL_SYSTEM_PATTERN,

    OCR_ARTIFACT_PATTERN,

    SYMBOL_GARBAGE_PATTERN,
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


# ─────────────────────────────────────────────────────────────
# TOKENIZATION
# Tables require conservative token handling because:
# - structure matters
# - delimiters matter
# - IDs matter
# - numerics matter
# ─────────────────────────────────────────────────────────────

TOKEN_SPLIT_PATTERN = re.compile(r"(\s+)")


# ─────────────────────────────────────────────────────────────
# NUMERAL NORMALIZATION MAPS
# Convert multilingual numerals into ASCII numerals
# for stable downstream retrieval/indexing.
# ─────────────────────────────────────────────────────────────

NUMERAL_NORMALIZATION_MAP = {

    # Gujarati
    "૦": "0",
    "૧": "1",
    "૨": "2",
    "૩": "3",
    "૪": "4",
    "૫": "5",
    "૬": "6",
    "૭": "7",
    "૮": "8",
    "૯": "9",

    # Bengali
    "০": "0",
    "১": "1",
    "২": "2",
    "৩": "3",
    "৪": "4",
    "৫": "5",
    "৬": "6",
    "৭": "7",
    "৮": "8",
    "৯": "9",

    # Kannada
    "೦": "0",
    "೧": "1",
    "೨": "2",
    "೩": "3",
    "೪": "4",
    "೫": "5",
    "೬": "6",
    "೭": "7",
    "೮": "8",
    "೯": "9",

    # Devanagari
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}


# ─────────────────────────────────────────────────────────────
# SAFE STRUCTURAL TOKENS
# These must be preserved because table data heavily
# depends on structure and references.
# ─────────────────────────────────────────────────────────────

def is_safe_structural_token(
    token: str
) -> bool:

    if URL_PATTERN.search(token):
        return True

    if EMAIL_PATTERN.search(token):
        return True

    if PHONE_PATTERN.search(token):
        return True

    if FILE_REF_PATTERN.match(token):

        if len(token) >= 4:
            return True

    return False


# ─────────────────────────────────────────────────────────────
# MULTILINGUAL NUMERAL NORMALIZATION
#
# Example:
#   ೦೩೨೦ → 0320
#   ০২৪০ → 0240
#
# This is critical for:
# - table retrieval
# - numeric indexing
# - downstream filtering
# ─────────────────────────────────────────────────────────────

def normalize_multilingual_numerals(
    token: str
) -> str:

    normalized = []

    for ch in token:

        normalized.append(
            NUMERAL_NORMALIZATION_MAP.get(ch, ch)
        )

    return "".join(normalized)


# ─────────────────────────────────────────────────────────────
# SYMBOL ARTIFACT NORMALIZATION
#
# Conservative cleanup because symbols may contain
# structural meaning inside tables.
# ─────────────────────────────────────────────────────────────

def normalize_table_symbol_noise(
    token: str
) -> str:

    token = token.replace("£", "")
    token = token.replace("°", "")
    token = token.replace("॥", " ")
    token = token.replace("।।", " ")

    token = re.sub(
        r"[|]{3,}",
        "||",
        token
    )

    token = re.sub(
        r"[-]{3,}",
        "--",
        token
    )

    return token.strip()


# ─────────────────────────────────────────────────────────────
# OCR TABLE ARTIFACT FILTERING
#
# Conservative strategy:
# - preserve long structured references
# - remove highly suspicious short artifacts
# ─────────────────────────────────────────────────────────────

def remove_table_ocr_artifacts(
    token: str
) -> str:

    if is_safe_structural_token(token):
        return token

    if OCR_ARTIFACT_PATTERN.search(token):

        # Preserve potentially meaningful structured refs
        if len(token) >= 8:
            return token

        logger.debug(
            f"Removed table OCR artifact: {token}"
        )

        return ""

    return token


# ─────────────────────────────────────────────────────────────
# STRUCTURE-SAFE TOKEN NORMALIZATION
#
# Tables require:
# - preserving separators
# - preserving spacing
# - preserving delimiters
# ─────────────────────────────────────────────────────────────

def normalize_table_token(
    token: str
) -> str:

    if not token.strip():
        return token

    # --------------------------------------------------------
    # Preserve structural tokens
    # --------------------------------------------------------

    if is_safe_structural_token(token):

        return token

    # --------------------------------------------------------
    # Normalize multilingual numerals
    # --------------------------------------------------------

    if MIXED_NUMERAL_SYSTEM_PATTERN.search(token):

        token = normalize_multilingual_numerals(
            token
        )

    # --------------------------------------------------------
    # Normalize symbol noise
    # --------------------------------------------------------

    if SYMBOL_GARBAGE_PATTERN.search(token):

        token = normalize_table_symbol_noise(
            token
        )

    # --------------------------------------------------------
    # Remove OCR table artifacts conservatively
    # --------------------------------------------------------

    token = remove_table_ocr_artifacts(token)

    return token


# ─────────────────────────────────────────────────────────────
# FINAL TABLE SPACING NORMALIZATION
#
# Conservative because aggressive spacing cleanup
# can destroy table structure.
# ─────────────────────────────────────────────────────────────

def normalize_table_spacing(
    text: str
) -> str:

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ─────────────────────────────────────────────────────────────
# MAIN TABLE CLEANUP PIPELINE
# ─────────────────────────────────────────────────────────────

def clean_table_text(
    text: str
) -> str:

    """
    Structure-preserving OCR cleanup pipeline for tables.

    Responsibilities:
    - multilingual numeral normalization
    - OCR symbol cleanup
    - table artifact reduction
    - structure-safe normalization

    This module intentionally avoids:
    - aggressive semantic cleanup
    - multilingual script removal
    - contextual reconstruction
    - row merging
    - delimiter destruction

    Table cleanup is intentionally conservative
    because structural integrity is critical for:
    - retrieval
    - indexing
    - downstream analytics
    """

    if not text:
        return text

    tokens = TOKEN_SPLIT_PATTERN.split(text)

    original_tokens = len(tokens)

    cleaned_tokens = []

    normalized_count = 0

    removed_count = 0

    for token in tokens:

        original_token = token

        token = normalize_table_token(token)

        if not token:

            removed_count += 1
            continue

        if token != original_token:

            normalized_count += 1

        cleaned_tokens.append(token)

    cleaned_text = "".join(cleaned_tokens)

    cleaned_text = normalize_table_spacing(
        cleaned_text
    )

    logger.info(
        f"Table cleanup completed | "
        f"Original tokens: {original_tokens} | "
        f"Normalized: {normalized_count} | "
        f"Removed: {removed_count}"
    )

    return cleaned_text