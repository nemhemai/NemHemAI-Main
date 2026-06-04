# app/ocr_v2/cleanup/script_cleanup.py

import logging
import re

from collections import defaultdict
from typing import Dict

from app.ocr_v2.languages.gujarati.script_policy import (

    should_preserve_gujarati_token,

    should_preserve_latin_token,

    should_remove_foreign_fragment,
)

from app.ocr_v2.patterns import (

    SCRIPT_RANGES,

    FOREIGN_SCRIPTS,

    URL_PATTERN,

    EMAIL_PATTERN,

    PHONE_PATTERN,

    FILE_REF_PATTERN,

    MIXED_NUMERAL_SYSTEM_PATTERN,

    FOREIGN_DOMINANT_TOKEN_PATTERN,
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
# SCRIPT DETECTION
# ─────────────────────────────────────────────────────────────

def detect_scripts(token: str) -> Dict[str, int]:

    """
    Detect script distribution inside a token.

    Example:
        "ગુજરાત" →
            {"gujarati": 7}

        "ABCதமிழ்" →
            {
                "latin": 3,
                "tamil": 5
            }
    """

    counts = defaultdict(int)

    for ch in token:

        cp = ord(ch)

        for script, (start, end) in SCRIPT_RANGES.items():

            if start <= cp <= end:

                counts[script] += 1
                break

    return dict(counts)


# ─────────────────────────────────────────────────────────────
# SAFE STRUCTURAL TOKENS
# These should generally NOT be removed because
# they may represent:
# - URLs
# - file references
# - phone numbers
# - IDs
# - metadata
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
# FOREIGN SCRIPT DOMINANCE
# Used to avoid aggressive removal of mixed tokens.
# ─────────────────────────────────────────────────────────────

def foreign_script_ratio(
    token: str,
    scripts: Dict[str, int]
) -> float:

    total = sum(scripts.values())

    if total == 0:
        return 0.0

    foreign_count = sum(

        count

        for script, count in scripts.items()

        if script in FOREIGN_SCRIPTS
    )

    return foreign_count / total


# ─────────────────────────────────────────────────────────────
# SAFE LEAKAGE FILTERING
# ─────────────────────────────────────────────────────────────

def should_remove_token(token: str) -> bool:

    """
    Conservative multilingual OCR cleanup.

    This stage ONLY removes:
    - isolated foreign-script leakage
    - dominant multilingual OCR noise
    - mixed numeral contamination

    This stage intentionally avoids:
    - semantic reconstruction
    - hallucination repair
    - contextual rewriting
    """

    token = token.strip()

    if not token:
        return False

    # --------------------------------------------------------
    # Preserve structural tokens
    # --------------------------------------------------------

    if is_safe_structural_token(token):
        return False

    scripts = detect_scripts(token)

    if not scripts:
        return False

    # --------------------------------------------------------
    # Gujarati preservation policy
    # --------------------------------------------------------

    if should_preserve_gujarati_token(
        token,
        scripts
    ):
        return False
    
    # --------------------------------------------------------
    # Latin preservation policy
    # --------------------------------------------------------

    if should_preserve_latin_token(
        token,
        scripts
    ):
        return False
    
    
    
    # --------------------------------------------------------
    # Mixed numeral contamination
    # Example:
    #   ૦૨4૩२
    #   ೦೩20
    # --------------------------------------------------------

    if MIXED_NUMERAL_SYSTEM_PATTERN.search(token):

        logger.debug(
            f"Mixed numeral corruption detected: {token}"
        )

        return True

    # --------------------------------------------------------
    # Foreign script presence
    # --------------------------------------------------------

    present_foreign = FOREIGN_SCRIPTS.intersection(
        scripts.keys()
    )

    if not present_foreign:
        return False

    # --------------------------------------------------------
    # Gujarati foreign leakage policy
    # --------------------------------------------------------

    if should_remove_foreign_fragment(
        token,
        scripts
    ):

        logger.debug(
            f"Short foreign leakage removed: {token}"
        )

        return True

    # --------------------------------------------------------
    # Foreign-dominant multilingual tokens
    # Example:
    #   ஸ்.PDF
    #   ೦೩೨೦-AB
    # --------------------------------------------------------

    if FOREIGN_DOMINANT_TOKEN_PATTERN.search(token):

        logger.debug(
            f"Foreign dominant token removed: {token}"
        )

        return True

    # --------------------------------------------------------
    # Foreign dominance ratio analysis
    # Prevent over-removing mixed semantic tokens.
    # --------------------------------------------------------

    ratio = foreign_script_ratio(
        token,
        scripts
    )

    if ratio >= 0.70:

        logger.debug(
            f"Foreign-heavy OCR leakage removed: {token}"
        )

        return True

    return False


# ─────────────────────────────────────────────────────────────
# MAIN CLEANUP PIPELINE
# ─────────────────────────────────────────────────────────────

def remove_mixed_script_noise(text: str) -> str:

    """
    Remove deterministic multilingual OCR leakage.

    This module focuses ONLY on:
    - script contamination
    - multilingual OCR leakage
    - mixed numeral corruption

    This module DOES NOT:
    - repair hallucinated tokens
    - reconstruct semantics
    - normalize OCR spellings
    - perform contextual repair

    Those stages are handled separately in:
    - normalization.py
    - repair.py
    - future semantic layers
    """

    if not text:
        return text

    tokens = TOKEN_SPLIT_PATTERN.split(text)

    cleaned_tokens = []

    removed_tokens = 0

    for token in tokens:

        token = token.strip()

        if not token:
            continue

        if should_remove_token(token):

            removed_tokens += 1

            logger.debug(
                f"Removed script leakage token: {token}"
            )

            continue

        cleaned_tokens.append(token)

    cleaned_text = " ".join(cleaned_tokens)

    cleaned_text = re.sub(
        r"\s+",
        " ",
        cleaned_text
    ).strip()

    logger.info(
        f"Script cleanup completed | "
        f"Original tokens: {len(tokens)} | "
        f"Removed: {removed_tokens} | "
        f"Remaining: {len(cleaned_tokens)}"
    )

    return cleaned_text