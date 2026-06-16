# app/ocr_v2/languages/gujarati/noise_policy.py

# ============================================================
# GUJARATI OCR NOISE POLICY
#
# Responsibilities:
# - Gujarati OCR glyph repair policy
# - Gujarati deterministic repair orchestration
# - Gujarati repair-map application
#
# IMPORTANT:
# This module should ONLY contain Gujarati-specific
# OCR repair decisions.
#
# Generic OCR cleanup orchestration belongs in:
# cleanup/noise.py
# ============================================================

from typing import List

from app.ocr_v2.core.language_router import (
    route_language_processing
)


# ─────────────────────────────────────────────────────────────
# GUJARATI GLYPH REPAIR
# ─────────────────────────────────────────────────────────────

def apply_gujarati_glyph_repairs(
    tokens: List[str]
) -> List[str]:

    """
    Apply Gujarati OCR repair-map substitutions.

    Examples:
    - ƨ → સ
    - Ȣ → ક
    - સાંƨ Ȣૃિતક → સાંસ્કૃતિક

    Conservative deterministic repair only.
    """

    repaired_tokens = []

    routing = route_language_processing(
        " ".join(tokens)
    )

    repair_map = routing["repair_map"]

    for token in tokens:

        repaired_token = token

        for broken, fixed in repair_map.items():

            if broken in repaired_token:

                repaired_token = repaired_token.replace(
                    broken,
                    fixed
                )

        repaired_tokens.append(
            repaired_token
        )

    return repaired_tokens