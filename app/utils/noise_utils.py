# app/utils/noise_utils.py 

"""
noise_utils.py
────────────────────────────────────────────────────────────────────────
Noise detection utilities for government document extraction.

This module contains:
• Noise pattern compilation
• Text noise detection
• Cover page detection
"""

import re


# ──────────────────────────────────────────────────────────────────────
# COMPILE NOISE PATTERNS
# ──────────────────────────────────────────────────────────────────────

def compile_noise_patterns():
    """
    Compile regex patterns used to filter document noise such as:

    • page numbers
    • government boilerplate
    • OCR artifacts
    • confidentiality stamps
    """

    patterns = [

        # Page furniture
        r"^page\s+\d+\s*(of\s+\d+)?$",
        r"^\d+\s*of\s*\d+$",
        r"^\d+$",
        r"^-\s*\d+\s*-$",

        # OCR artifacts
        r"^[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z0-9]{2,},?$",
        r"^\|\s*\(",

        # Confidentiality stamps
        r"private\s+and\s+confidential",
        r"^confidential$",
        r"^strictly\s+confidential",
        r"^draft$",

        # Government letterhead
        r"^government of ",
        r"^ministry of ",
        r"^department of ",

        # Gazette markers
        r"^\[?भाग\s+[IVX\d]+",
        r"^राजपत्र",
        r"^official\s+gazette",

        # Legal print boilerplate
        r"copyright.*reserved",
        r"^all rights reserved",
        r"printed\s+at\s+",

        # TOC dotted leaders
        r"\.{4,}\s*\d+\s*$",
    ]

    return [re.compile(p, re.IGNORECASE) for p in patterns]


# ──────────────────────────────────────────────────────────────────────
# NOISE DETECTION
# ──────────────────────────────────────────────────────────────────────

def is_noise(text, element_type, noise_patterns):
    """
    Determine whether a text element should be treated as noise.
    """

    # Filter page headers/footers
    if element_type in ("page_header", "page_footer"):
        return True

    # Very short fragments
    if len(text.strip()) < 3:
        return True

    text_stripped = text.strip()

    return any(pattern.search(text_stripped) for pattern in noise_patterns)


# ──────────────────────────────────────────────────────────────────────
# COVER PAGE DETECTION
# ──────────────────────────────────────────────────────────────────────

def is_cover_page(page_texts):
    """
    Detect cover pages dominated by logos, seals, or minimal text.
    """

    if not page_texts:
        return True

    total_words = sum(len(t.split()) for t in page_texts)

    # Very few words → likely cover
    if total_words < 1:
        return True

    return False

def is_small_artifact(text):
    """
    Detect small OCR fragments like '७0:' or 'क्व'.
    """

    if not text:
        return True

    t = text.strip()

    # Very short fragments
    if len(t) <= 3:
        return True

    # Very small token count
    if len(t.split()) == 1 and len(t) < 5:
        return True

    # Mostly punctuation / symbols
    if sum(c.isalnum() for c in t) <= 2:
        return True

    return False