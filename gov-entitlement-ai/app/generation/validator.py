# app/generation/validator.py

import re


VALUE_PATTERN = re.compile(
    r'\d+(?:[\.\-–]\d+)*\s*(?:µg/m3|mg/m3|ppm|ppb|%|₹|rs\.?|crore|lakh)?',
    re.IGNORECASE
)


def extract_values(text: str) -> set:
    """
    Extract numeric values from text
    """
    matches = VALUE_PATTERN.findall(text or "")
    return set(m.strip().lower() for m in matches)


def validate_answer(answer: str, context: str, query_analysis: dict) -> dict:
    """
    Validates if answer is grounded in context
    Applies strict validation ONLY for numeric/financial queries
    """

    query_type = query_analysis.get("query_type", "mixed")

    # ─────────────────────────────────────────────────────────────
    # 🚫 SKIP VALIDATION FOR NON-NUMERIC QUERIES
    # ─────────────────────────────────────────────────────────────
    if query_type not in ["numeric", "financial"]:
        return {
            "is_valid": True,
            "reason": "Validation skipped for non-numeric query"
        }

    # ─────────────────────────────────────────────────────────────
    # 🔢 NUMERIC VALIDATION
    # ─────────────────────────────────────────────────────────────

    answer_values = extract_values(answer)
    context_values = extract_values(context)

    missing_values = answer_values - context_values

    if missing_values:
        return {
            "is_valid": False,
            "reason": f"Values not grounded: {missing_values}"
        }

    return {
        "is_valid": True,
        "reason": "All values grounded"
    }