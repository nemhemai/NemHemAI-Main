# app/ocr_v2/languages/gujarati/script_policy.py

# ============================================================
# GUJARATI SCRIPT CLEANUP POLICY
#
# Responsibilities:
# - Gujarati preservation policy
# - Gujarati multilingual tolerance
# - Gujarati leakage filtering policy
#
# IMPORTANT:
# This module should contain ONLY Gujarati-specific
# cleanup decisions.
#
# Generic cleanup orchestration belongs in:
# cleanup/script_cleanup.py
# ============================================================


# ─────────────────────────────────────────────────────────────
# GUJARATI FOREIGN SCRIPT POLICY
# ─────────────────────────────────────────────────────────────

GUJARATI_FOREIGN_SCRIPTS = {

    "bengali",

    "oriya",

    "tamil",

    "telugu",

    "kannada",

    "malayalam",
}


# ─────────────────────────────────────────────────────────────
# GUJARATI TOKEN PRESERVATION
# ─────────────────────────────────────────────────────────────

def should_preserve_gujarati_token(
    token: str,
    scripts: dict
) -> bool:

    """
    Preserve Gujarati-containing tokens.

    Gujarati OCR often generates:
    - mixed fragments
    - broken conjuncts
    - multilingual contamination

    Aggressive removal may destroy semantics.
    """

    if "gujarati" in scripts:

        return True

    return False


# ─────────────────────────────────────────────────────────────
# LATIN TOKEN PRESERVATION
# ─────────────────────────────────────────────────────────────

def should_preserve_latin_token(
    token: str,
    scripts: dict
) -> bool:

    """
    Preserve Latin fragments because Gujarati
    government PDFs frequently contain:
    - English department names
    - abbreviations
    - office names
    - metadata
    - technical references
    """

    if "latin" in scripts:

        return True

    return False


# ─────────────────────────────────────────────────────────────
# FOREIGN LEAKAGE REMOVAL POLICY
# ─────────────────────────────────────────────────────────────

def should_remove_foreign_fragment(
    token: str,
    scripts: dict
) -> bool:

    """
    Conservative Gujarati OCR leakage filtering.

    Remove:
    - short isolated foreign fragments

    Preserve:
    - longer multilingual semantic fragments
    """

    present_foreign = (
        GUJARATI_FOREIGN_SCRIPTS.intersection(
            scripts.keys()
        )
    )

    if present_foreign:

        if len(token.strip()) <= 4:

            return True

    return False