# app/ocr_v2/cleanup/noise.py

import logging
import re

from typing import List

from app.ocr_v2.languages.gujarati.noise_policy import (
    apply_gujarati_glyph_repairs
)

from app.ocr_v2.patterns import (

    BROKEN_GLYPH_MAP,

    CORRUPTED_NUMERIC_PATTERN,

    SYMBOL_GARBAGE_PATTERN,

    OCR_ARTIFACT_PATTERN,

    MULTISCRIPT_PUNCT_PATTERN,

    URL_PATTERN,

    EMAIL_PATTERN,

    PHONE_PATTERN,

    FILE_REF_PATTERN,

    MIXED_NUMERAL_SYSTEM_PATTERN,
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
# ─────────────────────────────────────────────────────────────

TOKEN_SPLIT_PATTERN = re.compile(r"\s+")


# ─────────────────────────────────────────────────────────────
# SAFE STRUCTURAL TOKENS
# These tokens should generally be preserved because
# they may contain:
# - IDs
# - phone numbers
# - URLs
# - file references
# - structured metadata
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

        if len(token) >= 6:
            return True

    return False


# ─────────────────────────────────────────────────────────────
# BROKEN OCR GLYPH REPAIR
# This stage repairs deterministic OCR glyph corruption.
#
# Example:
#   ƨ → સ
#   Ȣ → ક
# ─────────────────────────────────────────────────────────────

def repair_broken_glyphs(
    tokens: List[str]
):

    """
    Deterministic OCR glyph repair orchestration.

    Gujarati-specific repair policy is delegated to:
    languages/gujarati/noise_policy.py

    Future:
    - Hindi repair policy
    - Marathi repair policy
    - English OCR repair policy
    """

    repaired_tokens = apply_gujarati_glyph_repairs(
        tokens
    )

    repaired_count = sum(

        1

        for original, repaired in zip(
            tokens,
            repaired_tokens
        )

        if original != repaired
    )

    logger.info(
        f"Broken glyph repairs applied: {repaired_count}"
    )

    return repaired_tokens

# ─────────────────────────────────────────────────────────────
# MIXED NUMERAL NORMALIZATION
# Normalize OCR numeric corruption while preserving
# structural numeric information whenever possible.
#
# This stage is intentionally conservative.
# ─────────────────────────────────────────────────────────────

def normalize_corrupted_numeric_tokens(
    tokens: List[str]
):

    cleaned = []

    normalized = 0

    for token in tokens:

        # Preserve structural references
        if is_safe_structural_token(token):

            cleaned.append(token)
            continue

        if MIXED_NUMERAL_SYSTEM_PATTERN.search(token):

            repaired = re.sub(
                r"[£$°]",
                "",
                token
            )

            repaired = re.sub(
                r"[-–—]{2,}",
                "-",
                repaired
            )

            normalized += 1

            cleaned.append(repaired)

            continue

        if CORRUPTED_NUMERIC_PATTERN.search(token):

            repaired = re.sub(
                r"[£$°]",
                "",
                token
            )

            repaired = re.sub(
                r"[_]{2,}",
                "_",
                repaired
            )

            normalized += 1

            cleaned.append(repaired)

            continue

        cleaned.append(token)

    logger.info(
        f"Normalized corrupted numeric tokens: {normalized}"
    )

    return cleaned


# ─────────────────────────────────────────────────────────────
# SYMBOL GARBAGE NORMALIZATION
# Remove residual OCR symbols while preserving
# semantic content whenever possible.
# ─────────────────────────────────────────────────────────────

def normalize_symbol_garbage(
    tokens: List[str]
):

    cleaned = []

    normalized = 0

    for token in tokens:

        if is_safe_structural_token(token):

            cleaned.append(token)
            continue

        if SYMBOL_GARBAGE_PATTERN.search(token):

            repaired = token

            repaired = repaired.replace("£", "")
            repaired = repaired.replace("°", "")
            repaired = repaired.replace("&", "")

            repaired = re.sub(
                r"[’]{2,}",
                "'",
                repaired
            )

            repaired = repaired.strip()

            # Remove only if completely empty
            if not repaired:

                normalized += 1
                continue

            normalized += 1

            cleaned.append(repaired)

            continue

        cleaned.append(token)

    logger.info(
        f"Normalized symbol garbage tokens: {normalized}"
    )

    return cleaned


# ─────────────────────────────────────────────────────────────
# MULTISCRIPT PUNCTUATION NORMALIZATION
#
# Example:
#   ॥
#   ।।
#   duplicated OCR punctuation
# ─────────────────────────────────────────────────────────────

def normalize_multiscript_punctuation(
    tokens: List[str]
):

    cleaned = []

    normalized = 0

    for token in tokens:

        if MULTISCRIPT_PUNCT_PATTERN.search(token):

            repaired = token

            repaired = repaired.replace("॥", " ")
            repaired = repaired.replace("।।", " ")
            repaired = repaired.replace("।", " ")

            repaired = repaired.strip()

            if not repaired:

                normalized += 1
                continue

            normalized += 1

            cleaned.append(repaired)

            continue

        cleaned.append(token)

    logger.info(
        f"Normalized multiscript punctuation: {normalized}"
    )

    return cleaned


# ─────────────────────────────────────────────────────────────
# OCR ARTIFACT DETECTION
#
# This stage removes only highly corrupted OCR artifacts.
#
# IMPORTANT:
# We avoid aggressive deletion because many tokens may still
# contain recoverable semantic information.
# ─────────────────────────────────────────────────────────────

def remove_residual_ocr_artifacts(
    tokens: List[str]
):

    cleaned = []

    removed = 0

    for token in tokens:

        if is_safe_structural_token(token):

            cleaned.append(token)
            continue

        if OCR_ARTIFACT_PATTERN.search(token):

            # preserve longer potentially meaningful fragments
            if len(token) > 8:

                cleaned.append(token)
                continue

            removed += 1
            continue

        cleaned.append(token)

    logger.info(
        f"Removed residual OCR artifacts: {removed}"
    )

    return cleaned


# ─────────────────────────────────────────────────────────────
# SPACING NORMALIZATION
#
# Normalize excessive OCR spacing artifacts while
# preserving semantic structure.
# ─────────────────────────────────────────────────────────────

def normalize_spacing_artifacts(
    text: str
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    text = re.sub(
        r"\s+([,.;:])",
        r"\1",
        text
    )

    return text.strip()


# ─────────────────────────────────────────────────────────────
# MAIN OCR NOISE PIPELINE
# ─────────────────────────────────────────────────────────────

def filter_ocr_noise(text: str) -> str:

    """
    OCR artifact refinement layer.

    Responsibilities:
    - deterministic glyph repair
    - numeric artifact normalization
    - OCR symbol cleanup
    - punctuation cleanup
    - residual OCR artifact filtering

    This module DOES NOT:
    - remove multilingual script leakage
    - perform semantic reconstruction
    - hallucination correction
    - contextual repair

    Those responsibilities belong to:
    - script_cleanup.py
    - repair.py
    - future semantic layers
    """

    if not text:
        return text

    tokens = TOKEN_SPLIT_PATTERN.split(text)

    original_count = len(tokens)

    # --------------------------------------------------------
    # REPAIR-FIRST PIPELINE
    # --------------------------------------------------------

    tokens = repair_broken_glyphs(tokens)

    tokens = normalize_corrupted_numeric_tokens(tokens)

    tokens = normalize_symbol_garbage(tokens)

    tokens = normalize_multiscript_punctuation(tokens)

    tokens = remove_residual_ocr_artifacts(tokens)

    # --------------------------------------------------------
    # FINAL NORMALIZATION
    # --------------------------------------------------------

    cleaned_text = " ".join(tokens)

    cleaned_text = normalize_spacing_artifacts(
        cleaned_text
    )

    logger.info(
        f"OCR noise filtering completed | "
        f"Original tokens: {original_count} | "
        f"Remaining tokens: {len(tokens)}"
    )

    return cleaned_text