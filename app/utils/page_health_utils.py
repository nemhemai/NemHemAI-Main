# app/utils/page_health_utils.py

"""
page_health_utils.py

Utilities for evaluating extraction quality of a single page
after Docling layout processing.
"""

def evaluate_page_health(elements):
    """
    Compute extraction health metrics for a page.
    """

    element_count = len(elements)

    text_length = sum(
        len(e.get("content_original", ""))
        for e in elements
        if e.get("element_type") in ["paragraph", "clause", "section", "heading"]
    )

    token_count = sum(
        e.get("token_count", 0)
        for e in elements
    )

    table_count = sum(
        1 for e in elements if e.get("element_type") == "table"
    )

    return {
        "element_count": element_count,
        "text_length": text_length,
        "token_count": token_count,
        "tables": table_count
    }


def classify_page_health(health):
    """
    Classify extraction quality.
    """

    if health["tables"] >= 1:
        return "good"

    if health["element_count"] == 0:
        return "failed"

    if health["element_count"] < 3 and health["text_length"] < 50:
        return "weak"

    return "good"