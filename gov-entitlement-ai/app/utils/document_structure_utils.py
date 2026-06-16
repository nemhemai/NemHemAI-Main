# app/utils/document_structure_utils.py

import re

def is_toc_page(page_texts):

    if not page_texts:
        return False

    first_lines = " ".join(page_texts[:5]).upper()

    if any(k in first_lines for k in [
        "TABLE OF CONTENTS",
        "CONTENTS",
        "INDEX",
        "LIST OF CHAPTERS",
        "अनुक्रमणिका"
    ]):
        return True

    # patterns
    numbered_pattern = re.compile(r"^\s*[०-९0-9]+\)")
    isolated_number = re.compile(r"^[०-९0-9]+\)$")
    page_number = re.compile(r"^[०-९0-9]{1,3}$")

    numbered_lines = 0
    short_numeric = 0

    for text in page_texts:

        t = text.strip()

        if numbered_pattern.match(t):
            numbered_lines += 1

        if isolated_number.match(t):
            short_numeric += 1

        if page_number.match(t):
            short_numeric += 1

    total = len(page_texts)

    # heuristics for Indian government TOC
    if numbered_lines >= 3:
        return True

    if short_numeric >= 6:
        return True

    if (numbered_lines + short_numeric) / max(total,1) > 0.45:
        return True

    return False