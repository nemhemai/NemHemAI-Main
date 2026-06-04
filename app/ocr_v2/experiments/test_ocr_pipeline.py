# app/ocr_v2/experiments/test_ocr_pipeline.py

import json
from pathlib import Path
import re
from datetime import datetime

from app.ocr_v2.experiments.fetch_extracted_elements import (
    fetch_elements_by_document_ids
)

from app.ocr_v2.core.pipeline import correct_ocr_text

# ---------------------------------------------------
# OCRv2 DIAGNOSTIC HELPERS
# ---------------------------------------------------

def compute_diff(before: str, after: str):
    """
    Compare text before and after a pipeline stage.

    Used for:
    - detecting destructive cleanup
    - measuring removed characters
    - identifying changed stages
    """

    removed = max(0, len(before) - len(after))

    return {
        "changed": before != after,
        "chars_removed": removed,
        "length_before": len(before),
        "length_after": len(after),
    }


def estimate_corruption_score(text: str):
    """
    Estimate OCR corruption severity.

    Detects:
    - malformed OCR glyphs
    - unsupported Indic scripts
    - phantom Unicode artifacts
    - excessive OCR symbol noise
    """

    corruption_patterns = [

        # Broken OCR glyphs
        r"[ƨȢȤƣ£°]",

        # Tamil
        r"[\u0B80-\u0BFF]",

        # Telugu
        r"[\u0C00-\u0C7F]",

        # Kannada
        r"[\u0C80-\u0CFF]",

        # Malayalam
        r"[\u0D00-\u0D7F]",

        # Bengali/Oriya
        r"[\u0980-\u09FF]",
    ]

    corruption_count = 0

    for pattern in corruption_patterns:

        corruption_count += len(
            re.findall(pattern, text)
        )

    total_chars = max(len(text), 1)

    score = corruption_count / total_chars

    return round(score, 5)


DOCUMENT_IDS = [
    40,
    41,
    45,
    46,
    47
]

# ---------------------------------------------------
# BATCH PROCESSING MODE
# ---------------------------------------------------
"""
Run OCRv2 pipeline on Gujarati extracted elements
fetched from document_elements table.

Used for:
- OCR corruption discovery
- Gujarati OCR benchmarking
- OCR error taxonomy building
- future regression testing
- production-aligned OCR experiments
"""

print("\n" + "=" * 70)
print(f"Running OCRv2 Experiment on {len(DOCUMENT_IDS)} Gujarati Documents")
print("=" * 70)

# ---------------------------------------------------
# FETCH EXTRACTED ELEMENTS
# ---------------------------------------------------

elements = fetch_elements_by_document_ids(
    DOCUMENT_IDS
)

print(f"Fetched {len(elements)} extracted elements")

# ---------------------------------------------------
# OUTPUT DIRECTORY
# ---------------------------------------------------

OUTPUT_DIR = Path(
    "app/ocr_v2/experiments/output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# ---------------------------------------------------
# TIMESTAMP
# ---------------------------------------------------

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

# ---------------------------------------------------
# OUTPUT JSON FILE
# ---------------------------------------------------

OUTPUT_JSON = (
    OUTPUT_DIR
    / f"gujarati_docling_experiment_{timestamp}.json"
)

# ---------------------------------------------------
# EXPERIMENT METADATA
# ---------------------------------------------------

experiment_metadata = {

    "document_ids": DOCUMENT_IDS,

    "experiment_source": "document_elements",

    "ocr_pipeline_version": "OCRv2",

    "execution_timestamp": timestamp,
}

results = []

# ---------------------------------------------------
# APPLY OCR PIPELINE
# ---------------------------------------------------

for element in elements:

    page_no = element["page"]

    raw_text = element["raw_text"]

    pipeline_result = correct_ocr_text(raw_text)

    unicode_cleaned = pipeline_result[
        "unicode_cleaned"
    ]

    script_cleaned = pipeline_result[
        "script_cleaned"
    ]

    noise_filtered = pipeline_result[
        "noise_filtered"
    ]

    final_cleaned = pipeline_result[
        "final_cleaned"
    ]

    # ---------------------------------------------------
    # ELEMENT RESULT
    # ---------------------------------------------------

    results.append({

        "element_id": element["element_id"],

        "document_id": element["document_id"],

        "page": page_no,

        "element_type": element["element_type"],

        "sequence_order": element.get("sequence_order"),

        # ---------------------------------------------------
        # OCR DIAGNOSTICS
        # ---------------------------------------------------

        "diagnostics": {

            "corruption_scores": {

                "raw":
                estimate_corruption_score(
                    raw_text
                ),

                "unicode_cleaned":
                estimate_corruption_score(
                    unicode_cleaned
                ),

                "script_cleaned":
                estimate_corruption_score(
                    script_cleaned
                ),

                "noise_filtered":
                estimate_corruption_score(
                    noise_filtered
                ),

                "final_cleaned":
                estimate_corruption_score(
                    final_cleaned
                ),
            },

            "diffs": {

                "unicode_cleanup":
                compute_diff(
                    raw_text,
                    unicode_cleaned
                ),

                "script_cleanup":
                compute_diff(
                    unicode_cleaned,
                    script_cleaned
                ),

                "noise_filtering":
                compute_diff(
                    script_cleaned,
                    noise_filtered
                ),

                "final_cleanup":
                compute_diff(
                    noise_filtered,
                    final_cleaned
                ),
            }
        },

        # ---------------------------------------------------
        # PIPELINE OUTPUTS
        # ---------------------------------------------------

        "raw_text": raw_text,

        "unicode_cleaned": unicode_cleaned,

        "script_cleaned": script_cleaned,

        "noise_filtered": noise_filtered,

        "final_cleaned": final_cleaned
    })

# ---------------------------------------------------
# FINAL JSON STRUCTURE
# ---------------------------------------------------

final_output = {

    "metadata": experiment_metadata,

    "elements": results
}

# ---------------------------------------------------
# SAVE JSON
# ---------------------------------------------------

with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        final_output,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"\nSaved JSON:")
print(OUTPUT_JSON)

# ---------------------------------------------------
# OCR TEST COMPLETED
# ---------------------------------------------------

print("\n" + "=" * 70)
print("OCR PIPELINE TEST COMPLETED")
print("=" * 70)