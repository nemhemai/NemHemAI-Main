# app/generation/query_analyzer.py

import re
from typing import Dict, List

# 🧹 Stopwords to remove noise from entity extraction
STOPWORDS = {
    "what", "is", "are", "the", "of", "for", "to", "how",
    "can", "i", "be", "in", "on", "by", "with", "and",
    "or", "if", "my", "we", "do", "does", "did"
}

# ─────────────────────────────────────────────────────────────
# 🎯 GOVERNMENT QUERY KEYWORDS (EXPANDED + GENERIC)
# ─────────────────────────────────────────────────────────────

NUMERIC_KEYWORDS = {
    "value", "values", "range", "limit", "limits",
    "maximum", "minimum", "max", "min",
    "how much", "how many", "count", "number",
    "amount", "percentage", "ratio", "total", "standards",
    "cost","levels", "threshold"
}

DEFINITION_KEYWORDS = {
    "what is", "define", "meaning", "definition",
    "what are"
}

PROCEDURE_KEYWORDS = {
    "how to", "process", "procedure", "steps",
    "apply", "registration", "method",
    "submit", "obtain", "avail"
}

POLICY_KEYWORDS = {
    "rule", "rules", "policy", "guideline",
    "act", "law", "bye law", "notification",
    "circular", "order", "resolution",
    "provision", "as per", "according to",
    "section", "clause", "article", "schedule"
}

ELIGIBILITY_KEYWORDS = {
    "eligible", "eligibility", "who can apply",
    "criteria", "requirement", "qualification"
}

FINANCIAL_KEYWORDS = {
    "budget", "fund", "allocation", "cost",
    "expenditure", "revenue", "subsidy",
    "grant", "scheme amount", "financial"
}

EXPLANATION_KEYWORDS = {
    "why", "impact", "effect", "importance",
    "benefits", "purpose", "objective"
}


# ─────────────────────────────────────────────────────────────
# 🌐 MULTILINGUAL HINTS
# ─────────────────────────────────────────────────────────────

MARATHI_HINTS = {
    "काय", "कसे", "नियम", "अर्ज", "प्रक्रिया",
    "कोण", "पात्रता", "रक्कम"
}

GUJARATI_HINTS = {
    "શું", "કેવી રીતે", "નિયમ", "પ્રક્રિયા",
    "પાત્રતા", "રકમ"
}


# ─────────────────────────────────────────────────────────────
# 🔍 ENTITY DETECTION (STRONG + GENERIC)
# ─────────────────────────────────────────────────────────────

ENTITY_PATTERNS = [
    # Scientific / technical (PM2.5, NO2)
    r'\b[A-Z]{1,5}\d*\.?\d*\b',

    # Section / Rule / Clause references
    r'\b(section|rule|clause|article)\s*\d+[A-Za-z\-()]*\b',

    # GR / Circular / Notification numbers
    r'\b(GR|G\.R\.|No\.?|Notification|Circular)\s*[:\-]?\s*[A-Za-z0-9\/\-\._]+\b',

    # Form / Annexure
    r'\b(Form|Annexure|Schedule)\s*[A-Za-z0-9\-]+\b',

    # General alphanumeric codes (govt refs)
    r'\b[A-Z0-9]{3,}[-_/][A-Z0-9\-/]+\b'
]


def extract_entities(query: str) -> List[str]:
    """
    Clean + structured entity extraction

    Handles:
    - Section 4, Rule 5
    - GR No. XYZ/2020
    - PM2.5, NO2
    - Annexure II, Form A
    - Removes noise words
    """

    query_clean = query.strip()

    found = set()

    # ─────────────────────────────────────────────────────────────
    # 1. Structured legal references (HIGH PRIORITY)
    # ─────────────────────────────────────────────────────────────

    structured_patterns = [
        r'(Section\s+\d+[A-Za-z\-()]*)',
        r'(Rule\s+\d+[A-Za-z\-()]*)',
        r'(Clause\s+\(?[A-Za-z0-9]+\)?)',
        r'(Article\s+\d+)',
        r'(Schedule\s+[A-Za-z0-9\-]+)',
        r'(Form\s+[A-Za-z0-9\-]+)',
        r'(Annexure\s+[A-Za-z0-9\-]+)',
    ]

    for pattern in structured_patterns:
        matches = re.findall(pattern, query_clean, re.IGNORECASE)
        for m in matches:
            found.add(m.strip())

    # ─────────────────────────────────────────────────────────────
    # 2. Government codes (GR, Notification)
    # ─────────────────────────────────────────────────────────────

    code_patterns = [
        r'(GR\s*No\.?\s*[A-Za-z0-9\/\-\._]+)',
        r'(Notification\s*No\.?\s*[A-Za-z0-9\/\-\._]+)',
        r'([A-Z0-9]{3,}\/[A-Z0-9\/\-]+)'  # ENV/45 type
    ]

    for pattern in code_patterns:
        matches = re.findall(pattern, query_clean, re.IGNORECASE)
        for m in matches:
            found.add(m.strip())

    # ─────────────────────────────────────────────────────────────
    # 3. Scientific / uppercase tokens
    # ─────────────────────────────────────────────────────────────

    tokens = re.findall(r'\b[A-Za-z0-9\.]+\b', query)

    for t in tokens:
        t_clean = t.strip()

        # skip stopwords
        if t_clean.lower() in STOPWORDS:
            continue

        # keep meaningful patterns only
        if (
            re.match(r'^[A-Z]{2,}\d*\.?\d*$', t_clean)  # PM2.5, NO2
            or re.match(r'^[A-Z]{2,}$', t_clean)       # DBT, AI
        ):
            found.add(t_clean)

    return list(found)


# ─────────────────────────────────────────────────────────────
# 🧠 QUERY TYPE DETECTION
# ─────────────────────────────────────────────────────────────

def detect_query_type(query: str) -> str:
    q = query.lower()

    scores = {
        "numeric": sum(1 for k in NUMERIC_KEYWORDS if k in q),
        "definition": sum(1 for k in DEFINITION_KEYWORDS if k in q),
        "procedure": sum(1 for k in PROCEDURE_KEYWORDS if k in q),
        "policy_lookup": sum(1 for k in POLICY_KEYWORDS if k in q),
        "eligibility": sum(1 for k in ELIGIBILITY_KEYWORDS if k in q),
        "financial": sum(1 for k in FINANCIAL_KEYWORDS if k in q),
        "explanation": sum(1 for k in EXPLANATION_KEYWORDS if k in q),
    }

    # 🔥 pick dominant signal
    top_type = max(scores, key=scores.get)
    
    # 🌐 Marathi / Gujarati rule hint
    if any(w in q for w in ["नियम", "काय", "પ્રક્રિયા", "નિયમ"]):
        return "policy_lookup"

    # if no strong signal → mixed
    if scores[top_type] == 0:
        return "mixed"

    return top_type


# ─────────────────────────────────────────────────────────────
# 🎯 INTENT FLAGS
# ─────────────────────────────────────────────────────────────

def extract_intent_flags(query: str) -> Dict[str, bool]:
    q = query.lower()

    return {
        "asks_range": "range" in q,
        "asks_max": "maximum" in q or "max" in q,
        "asks_min": "minimum" in q or "min" in q,
        "asks_count": "count" in q or "number" in q,
        "asks_amount": "amount" in q or "cost" in q,
        "asks_procedure": any(k in q for k in ["how to", "process", "steps"]),
        "asks_eligibility": "eligibility" in q or "who can apply" in q,
        "asks_definition": any(k in q for k in ["what is", "define"]),
    }


# ─────────────────────────────────────────────────────────────
# 🌐 LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────────

def detect_language(query: str) -> str:
    """
    Detect query language using Unicode block ranges (reliable)
    + word-hint fallback for Marathi vs Hindi disambiguation.
    Supports: en, hi, mr, gu, ta, te, kn
    """
    import re

    # Gujarati Unicode block: U+0A80–U+0AFF
    if re.search(r"[\u0A80-\u0AFF]", query):
        return "gu"

    # Devanagari block covers both Hindi and Marathi: U+0900–U+097F
    if re.search(r"[\u0900-\u097F]", query):
        words = set(query.split())
        # Marathi-specific function words
        if words & {"आहे", "नाही", "आणि", "हे", "ते", "या", "काय", "कसे", "कोण", "अर्ज"}:
            return "mr"
        # Marathi query hints from MARATHI_HINTS
        if any(w in query for w in MARATHI_HINTS):
            return "mr"
        return "hi"

    # Tamil: U+0B80–U+0BFF
    if re.search(r"[\u0B80-\u0BFF]", query):
        return "ta"

    # Telugu: U+0C00–U+0C7F
    if re.search(r"[\u0C00-\u0C7F]", query):
        return "te"

    # Kannada: U+0C80–U+0CFF
    if re.search(r"[\u0C80-\u0CFF]", query):
        return "kn"

    return "en"


# ─────────────────────────────────────────────────────────────
# 🚀 MAIN ANALYZER
# ─────────────────────────────────────────────────────────────

def analyze_query(query: str) -> Dict:
    """
    Core control layer output
    """

    return {
        "query_type": detect_query_type(query),
        "entities": extract_entities(query),
        "intent": extract_intent_flags(query),
        "language": detect_language(query),
        "original_query": query
    }