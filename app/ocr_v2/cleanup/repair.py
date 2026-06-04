# app/ocr_v2/cleanup/repair.py

import logging
from app.ocr_v2.core.language_router import (
    route_language_processing
)


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


def repair_indic_confusions(
    text: str
) -> str:

    """
    Conservative deterministic OCR repair layer.

    Responsibilities:
    - apply language-specific repair maps
    - apply shared Indic OCR corrections
    - preserve semantic structure

    This module DOES NOT:
    - perform contextual reconstruction
    - hallucination repair
    - LLM semantic inference

    Those belong to future semantic repair layers.
    """

    if not text:
        return text

    routing = route_language_processing(
        text
    )

    repair_map = routing["repair_map"]

    repaired = text

    repair_count = 0

    for wrong, correct in repair_map.items():

        if wrong in repaired:

            repaired = repaired.replace(
                wrong,
                correct
            )

            repair_count += 1

    logger.info(
        f"Indic repair substitutions applied: "
        f"{repair_count}"
    )

    return repaired