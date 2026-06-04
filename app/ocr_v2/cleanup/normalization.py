# app/ocr_v2/cleanup/normalization.py

import logging
import re
from unicodedata import normalize

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


# ─────────────────────────────────────────────────────────────
# UNICODE CANONICALIZATION
# ─────────────────────────────────────────────────────────────
def canonicalize_unicode(text: str) -> str:
    """
    Normalize text to Unicode NFKC form and remove layout/control artifacts.
    """
    if not text:
        return text

    t = normalize("NFKC", text)
    t = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)  # zero-width chars
    t = re.sub(r"[‘’´`]", "'", t)                     # normalize apostrophes
    t = re.sub(r"[“”]", '"', t)                      # normalize quotes
    t = re.sub(r"[‐‑‒–—―]", "-", t)                  # dashes
    t = re.sub(r"\s+", " ", t).strip()               # spaces
    return t
