# app/ocr_v2/shared/indic_patterns.py

# ============================================================
# SHARED INDIC OCR REPAIR MAP
#
# Shared multilingual OCR correction knowledge used across:
# - Gujarati
# - Hindi
# - Marathi
# - English OCR artifacts
#
# IMPORTANT:
# This file should contain ONLY:
# - shared OCR hallucinations
# - multilingual OCR corruption
# - generic Indic cleanup
#
# Language-specific semantic rules belong in:
# languages/<language>/
# ============================================================

SHARED_INDIC_REPAIR_MAP = {

    # --------------------------------------------------------
    # ENGLISH OCR HALLUCINATIONS
    # --------------------------------------------------------

    "goverrnment": "government",
    "managment": "management",
    "managgement": "management",
    "corpporation": "corporation",
    "municipallity": "municipality",
    "committtee": "committee",
    "sectiion": "section",
    "notificaation": "notification",
    "authorizaation": "authorization",
    "departmennt": "department",
    "implementaation": "implementation",
    "byelawws": "byelaws",
    "schedulle": "schedule",
    "penallty": "penalty",
    "violaation": "violation",
    "compliiance": "compliance",
    "segregaation": "segregation",
    "waaste": "waste",
    "soliid": "solid",

    # --------------------------------------------------------
    # SHARED INDIC OCR CONFUSIONS
    # --------------------------------------------------------

    "धचनकचरा": "घनकचरा",
    "घनकचरराा": "घनकचरा",
    "कचरराा": "कचरा",

    "त्यावस्थापना": "व्यवस्थापन",
    "व्ययवस्थापन": "व्यवस्थापन",
    "व्यवस्थापनन": "व्यवस्थापन",

    "किवा": "किंवा",
    "कीवा": "किंवा",
    "किींवा": "किंवा",

    "ळाख": "लाख",
    "लाःख": "लाख",

    # --------------------------------------------------------
    # COMMON OCR SEMANTIC FAILURES
    # --------------------------------------------------------

    "fear": "किंवा",

    "R025": "2016",
}