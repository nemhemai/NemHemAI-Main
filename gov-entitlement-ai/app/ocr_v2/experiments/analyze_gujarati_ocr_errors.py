# app/ocr_v2/experiments/analyze_gujarati_ocr_errors.py

import json
import re

from pathlib import Path
from collections import defaultdict
from datetime import datetime
from app.ocr_v2.classification.corruption_classifier import (
    classify_token_corruption
)

from app.ocr_v2.patterns import (

    SCRIPT_RANGES,

    BROKEN_GLYPH_PATTERN,

    CORRUPTED_NUMERIC_PATTERN,

    SYMBOL_GARBAGE_PATTERN,

    OCR_ARTIFACT_PATTERN,

    ISOLATED_SCRIPT_LEAKAGE_PATTERN,

    MULTISCRIPT_PUNCT_PATTERN,
)


# ---------------------------------------------------
# INPUT / OUTPUT
# ---------------------------------------------------

INPUT_DIR = Path(
    "app/ocr_v2/experiments/output"
)

REPORTS_DIR = Path(
    "app/ocr_v2/experiments/reports"
)

REPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------
# TIMESTAMPED REPORT FILE
# ---------------------------------------------------

timestamp = datetime.now().strftime(
    "%Y-%m-%d %H:%M:%S"
)

timestamp_for_filename = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

OUTPUT_FILE = (
    REPORTS_DIR
    / f"gujarati_ocr_error_report_{timestamp_for_filename}.md"
)


# ---------------------------------------------------
# VALID ENGLISH / METADATA TOKENS
# ---------------------------------------------------

VALID_METADATA_TOKENS = {

    # government/admin
    "approved",
    "date",
    "file",
    "commissioner",
    "government",
    "india",
    "notification",
    "document",
    "adobe",
    "acrobat",
    "verify",
    "esign",
    "sign",
    "pdf",
    "ministry",
    "corporate",
    "affairs",
    "verified",
    "science",
    "calendar",
    "journey",
    "presents",
    "puzzles",
    "regional",

    # common english
    "of",
    "in",
    "to",
    "the",
    "for",
    "from",
    "with",
    "and",
    "on",
    "by",
    "at",
    "is",
    "as",

    # common OCR-safe terms
    "letter",
    "open",
    "page",
    "order",
    "copy",
    "rule",
    "rules",
    "part",

    # abbreviations
    "dc",
    "ias",
    "fd",
    "rti",
}


# ---------------------------------------------------
# REGEX PATTERNS
# ---------------------------------------------------


SUSPICIOUS_LATIN_PATTERN = re.compile(
    r"^[A-Za-z]{2,8}$"
)

TOKEN_SPLIT_PATTERN = re.compile(
    r"\s+"
)

# ---------------------------------------------------
# ANALYSIS STAGES
# ---------------------------------------------------

ANALYSIS_STAGES = [

    "raw_text",

    "unicode_cleaned",

    "script_cleaned",

    "noise_filtered",

    "final_cleaned",
]


# ---------------------------------------------------
# STORAGE
# ---------------------------------------------------

stage_line_tracking = []

classifier_errors = defaultdict(list)

pdf_scores = defaultdict(
    lambda: defaultdict(float)
)

pdf_error_counts = defaultdict(
    lambda: defaultdict(int)
)

element_type_scores = defaultdict(
    lambda: defaultdict(float)
)

element_type_error_counts = defaultdict(
    lambda: defaultdict(int)
)

# ---------------------------------------------------
# OCR CORRUPTION SEVERITY WEIGHTS
# ---------------------------------------------------

CATEGORY_WEIGHTS = {

    "semantic_multilingual_corruption": 1.00,

    "mixed_script_semantic_fragment": 0.95,

    "broken_glyph": 0.90,

    "isolated_script_leakage": 0.80,

    "corrupted_numeric": 0.70,

    "symbol_garbage": 0.55,

    "suspicious_latin_fragment": 0.30,
}


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def detect_scripts(token: str):

    detected = set()

    for ch in token:

        cp = ord(ch)

        for script, (start, end) in SCRIPT_RANGES.items():

            if start <= cp <= end:

                detected.add(script)

    return detected


def is_valid_metadata(token: str):

    token = token.lower()

    if token in VALID_METADATA_TOKENS:
        return True

    if token.startswith("http"):
        return True

    if "@" in token:
        return True

    if "/" in token and len(token) > 6:
        return True

    if re.match(r"^[A-Z]{2,10}$", token):
        return True

    return False


def is_suspicious_latin(token: str):

    token_lower = token.lower()

    # known clean english
    if token_lower in VALID_METADATA_TOKENS:
        return False

    # ignore title-case english words
    if token.istitle() and len(token) > 3:
        return False

    # suspicious OCR-like fragments
    suspicious_patterns = [

        r"[qxz]{2,}",
        r".*[0-9].*",
        r".*[£°$%#@].*",
    ]

    for pattern in suspicious_patterns:

        if re.search(pattern, token):
            return True

    # random uncommon short words
    uncommon = {

        "rissa",
        "mga",
        "orf",
        "ols",
        "aht",
        "ahl",
        "seq",
        "phere",
        "als",
        "anal",
        "ofiicer",
    }

    if token_lower in uncommon:
        return True

    # legitimate english-looking words
    if token.isalpha():

        vowel_count = sum(
            1 for ch in token.lower()
            if ch in "aeiou"
        )

        # likely real english word
        if vowel_count >= 2 and len(token) >= 5:
            return False

    return False


def is_symbol_heavy_corruption(token: str):

    if len(token) < 4:
        return False

    suspicious_symbols = set(
        "£°$#@&"
    )

    symbol_count = sum(

        1 for ch in token

        if ch in suspicious_symbols
    )

    ratio = symbol_count / len(token)

    # true OCR corruption
    if ratio >= 0.20:
        return True

    return False


def is_corrupted_numeric_fragment(token: str):

    # legitimate percentages
    if re.match(r"^[0-9०-९૦-૯]+%$", token):
        return False

    if CORRUPTED_NUMERIC_PATTERN.search(token):
        return True

    # legitimate decimals
    if re.match(r"^[0-9०-९૦-૯]+\.[0-9]+%?$", token):
        return False

    scripts = detect_scripts(token)

    indic_scripts = scripts - {"latin"}

    # multiple script numerals mixed
    if len(indic_scripts) > 1:
        return True

    # OCR-symbol corruption
    if re.search(r"[£°$]", token):

        if any(ch.isdigit() for ch in token):
            return True

    return False


def add_error(
    stage,
    category,
    json_file,
    line,
    token,
    classification=None,
    element_type=None
):

    classifier_errors[stage].append({

        "file": json_file.name,

        "line": line,

        "token": token,

        "corruption_type": category,

        "element_type": element_type,

        "repair_strategy":

            classification.get(
                "repair_strategy"
            )

            if classification else None,

        "repairable":

            classification.get(
                "repairable"
            )

            if classification else None,

        "llm_candidate":

            classification.get(
                "llm_candidate"
            )

            if classification else False,
    })

    weight = CATEGORY_WEIGHTS.get(
        category,
        0.5
    )

    pdf_scores[stage][json_file.name] += weight

    pdf_error_counts[stage][json_file.name] += 1

    if element_type:

        element_type_scores[stage][element_type] += weight

        element_type_error_counts[stage][element_type] += 1


def classify_ocr_quality(score):

    if score < 20:
        return "EXCELLENT"

    if score < 50:
        return "GOOD"

    if score < 100:
        return "MODERATE"

    if score < 200:
        return "POOR"

    return "VERY POOR"


# ---------------------------------------------------
# PROCESS JSON FILES
# ---------------------------------------------------

json_files = sorted(
    INPUT_DIR.glob("*.json")
)

print(f"\nFound {len(json_files)} OCR JSON files")


for json_file in json_files:

    print(f"\nAnalyzing: {json_file.name}")

    with open(json_file, "r", encoding="utf-8") as f:

        data = json.load(f)

    elements = data.get("elements", [])

    for element in elements:

        stage_line_tracking.append({

            "file": json_file.name,

            "document_id": element.get("document_id"),

            "element_id": element.get("element_id"),

            "element_type": element.get("element_type"),

            "page": element.get("page"),

            "raw_text":

                element.get(
                    "raw_text",
                    ""
                ),

            "unicode_cleaned":

                element.get(
                    "unicode_cleaned",
                    ""
                ),

            "script_cleaned":

                element.get(
                    "script_cleaned",
                    ""
                ),

            "noise_filtered":

                element.get(
                    "noise_filtered",
                    ""
                ),

            "final_cleaned":

                element.get(
                    "final_cleaned",
                    ""
                ),
        })

        for stage in ANALYSIS_STAGES:

            stage_text = element.get(stage, "")

            if not stage_text:
                continue

            lines = stage_text.splitlines()

            for line in lines:

                clean_line = line.strip()

                if not clean_line:
                    continue

                tokens = TOKEN_SPLIT_PATTERN.split(
                    clean_line
                )

                for token in tokens:

                    token = token.strip()

                    if not token:
                        continue

                    classification = classify_token_corruption(
                        token
                    )

                    corruption_type = classification[
                        "corruption_type"
                    ]

                    if corruption_type != "clean":

                        add_error(

                            stage,

                            corruption_type,

                            json_file,

                            clean_line,

                            token,

                            classification,

                            element.get("element_type")
                        )

                    # -----------------------------------------------
                    # SKIP METADATA
                    # -----------------------------------------------

                    if is_valid_metadata(token):
                        continue

                    scripts = detect_scripts(token)

                    # -----------------------------------------------
                    # LATIN FRAGMENTS
                    # -----------------------------------------------

                    if (
                        SUSPICIOUS_LATIN_PATTERN.match(token)
                        and is_suspicious_latin(token)
                    ):

                        add_error(
                            stage,
                            "suspicious_latin_fragment",
                            json_file,
                            clean_line,
                            token,
                            classification,
                            element.get("element_type")
                        )

                    # -----------------------------------------------
                    # NUMERIC CORRUPTION
                    # -----------------------------------------------

                    if is_corrupted_numeric_fragment(token):

                        add_error(
                            stage,
                            "corrupted_numeric_fragment",
                            json_file,
                            clean_line,
                            token,
                            classification,
                            element.get("element_type")
                        )

                    # -----------------------------------------------
                    # SCRIPT LEAKAGE
                    # -----------------------------------------------

                    if ISOLATED_SCRIPT_LEAKAGE_PATTERN.search(token):

                        add_error(
                            stage,
                            "isolated_script_leakage",
                            json_file,
                            clean_line,
                            token,
                            classification,
                            element.get("element_type")
                        )


# ---------------------------------------------------
# GENERATE REPORT
# ---------------------------------------------------

report_lines = []

report_lines.append(
    f"# Gujarati OCR Error Taxonomy Report ({timestamp})\n"
)

report_lines.append(
    f"Generated: {timestamp}\n"
)

report_lines.append(
    f"Total OCR JSON Files: {len(json_files)}\n"
)

# ---------------------------------------------------
# PDF OCR QUALITY SCORES
# ---------------------------------------------------

for stage in ANALYSIS_STAGES:

    report_lines.append("\n")
    report_lines.append(
        f"## PDF OCR QUALITY SCORES ({stage})\n"
    )

    sorted_pdf_scores = sorted(

        pdf_scores[stage].items(),

        key=lambda x: x[1]
    )

    for pdf_name, score in sorted_pdf_scores:

        quality = classify_ocr_quality(score)

        total_errors = pdf_error_counts[
            stage
        ][pdf_name]

        report_lines.append(

            f"- {pdf_name} "
            f"| Score: {score:.2f} "
            f"| Quality: {quality} "
            f"| Errors: {total_errors}"
        )

# ---------------------------------------------------
# ELEMENT TYPE ANALYTICS
# ---------------------------------------------------

for stage in ANALYSIS_STAGES:

    report_lines.append("\n")

    report_lines.append(
        f"## ELEMENT TYPE ANALYTICS ({stage})\n"
    )

    sorted_element_scores = sorted(

        element_type_scores[stage].items(),

        key=lambda x: x[1],

        reverse=True
    )

    for element_type, score in sorted_element_scores:

        total_errors = element_type_error_counts[
            stage
        ][element_type]

        quality = classify_ocr_quality(score)

        report_lines.append(

            f"- {element_type} "
            f"| Score: {score:.2f} "
            f"| Quality: {quality} "
            f"| Errors: {total_errors}"
        )

# ---------------------------------------------------
# OCR CORRUPTION TAXONOMY
# ---------------------------------------------------

for stage in ANALYSIS_STAGES:

    report_lines.append("\n")

    report_lines.append(
        f"# OCR CORRUPTION TAXONOMY ({stage})\n"
    )

    grouped = defaultdict(list)

    for item in classifier_errors[stage]:

        grouped[
            item["corruption_type"]
        ].append(item)

    sorted_groups = sorted(

        grouped.items(),

        key=lambda x: len(x[1]),

        reverse=True
    )

    for category, errors in sorted_groups:

        report_lines.append("\n")

        report_lines.append(
            f"## {category}\n"
        )

        report_lines.append(
            f"Detected Samples: {len(errors)}\n"
        )

        seen = set()

        unique_errors = []

        for err in errors:

            key = (
                err["line"],
                err["token"]
            )

            if key not in seen:

                unique_errors.append(err)

                seen.add(key)

        unique_errors = unique_errors[:20]

        for sample in unique_errors:

            report_lines.append(

                f"- TOKEN: `{sample['token']}`\n"

                f"  | Element Type: "
                f"{sample['element_type']}\n"

                f"  | Strategy: "
                f"{sample['repair_strategy']}\n"

                f"  | Repairable: "
                f"{sample['repairable']}\n"

                f"  | LLM Candidate: "
                f"{sample['llm_candidate']}\n"

                f"  → {sample['line']}\n"
            )

# ---------------------------------------------------
# STAGE-WISE CLEAN TEXT PREVIEW
# ---------------------------------------------------

report_lines.append("\n")

report_lines.append(
    "# STAGE-WISE CLEAN TEXT PREVIEW\n"
)

preview_samples = stage_line_tracking[:50]

for sample in preview_samples:

    report_lines.append("\n")

    report_lines.append(
        f"## FILE: {sample['file']} "
        f"| DOCUMENT: {sample['document_id']} "
        f"| ELEMENT: {sample['element_id']} "
        f"| TYPE: {sample['element_type']} "
        f"| PAGE: {sample['page']}\n"
    )

    report_lines.append(
        "### RAW TEXT\n"
    )

    report_lines.append(
        sample["raw_text"]
    )

    report_lines.append("\n")

    report_lines.append(
        "### UNICODE CLEANED\n"
    )

    report_lines.append(
        sample["unicode_cleaned"]
    )

    report_lines.append("\n")

    report_lines.append(
        "### SCRIPT CLEANED\n"
    )

    report_lines.append(
        sample["script_cleaned"]
    )

    report_lines.append("\n")

    report_lines.append(
        "### NOISE FILTERED\n"
    )

    report_lines.append(
        sample["noise_filtered"]
    )

    report_lines.append("\n")

    report_lines.append(
        "### FINAL CLEANED\n"
    )

    report_lines.append(
        sample["final_cleaned"]
    )

    report_lines.append("\n")

# ---------------------------------------------------
# SAVE REPORT
# ---------------------------------------------------

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write("\n".join(report_lines))


print("\n" + "=" * 70)
print("GUJARATI OCR ANALYSIS COMPLETED")
print("=" * 70)

print(f"\nSaved report:")
print(OUTPUT_FILE)
