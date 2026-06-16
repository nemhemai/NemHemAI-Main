# app/retrieval/query_expansion.py

"""
Query Intent Detection

Purpose:
Identify what type of query user is asking so we can adjust ranking accordingly.

Types:
- definition → "what is", "define"
- enforcement → penalty, violation, non-compliance
- table → numeric / structured queries
- general → fallback
"""
"""
def detect_query_type(query: str) -> str:
    q = query.lower()

    # Definition queries
    if any(x in q for x in ["define", "meaning", "what is"]):
        return "definition"

    # Enforcement / penalty queries
    if any(x in q for x in ["penalty", "fine", "violation", "non compliance", "non-compliance"]):
        return "enforcement"

    # Table / numeric queries
    if any(x in q for x in ["table", "schedule", "amount", "kg", "per day"]):
        return "table"

    return "general"

import re

# Generic Indian government domain synonyms
EXPANSION_MAP = {

    # Financial
    "charges": ["fees", "rates", "cost", "levy", "tariff"],
    "fee": ["charges", "rates", "cost"],

    # Legal
    "penalty": ["fine", "punishment", "violation", "offence"],
    "fine": ["penalty", "violation"],

    # Governance
    "authority": ["government", "department", "local body"],
    "government": ["authority", "agency"],

    # People
    "citizen": ["resident", "person", "occupier"],
    "person": ["citizen", "individual"],

    # Rules
    "rules": ["regulations", "guidelines", "law"],
    "regulation": ["rules", "law"],

    # Waste (extendable)
    "waste": ["garbage", "refuse", "solid waste"],

    # Actions
    "collection": ["pickup", "gathering"],
    "disposal": ["processing", "treatment"],
}


def expand_query(query: str, query_type: str) -> str:
    import re

    words = re.findall(r"\b\w+\b", query.lower())
    expanded_terms = set()

    for word in words:
        if word in EXPANSION_MAP:
            expanded_terms.update(EXPANSION_MAP[word])

    # 🔥 INTENT-AWARE EXPANSION (CRITICAL)

    if query_type == "table":
        expanded_terms.update([
            "schedule",
            "user fee",
            "user charges",
            "rates",
            "fees",
            "property tax"
        ])

    if query_type == "enforcement":
        expanded_terms.update([
            "penalty",
            "fine",
            "violation",
            "offence"
        ])

    if query_type == "definition":
        expanded_terms.update([
            "means",
            "defined as",
            "refers to"
        ])

    expanded_query = query + " " + " ".join(expanded_terms)

    return expanded_query.strip()"""
    

# app/retrieval/query_expansion.py
#
# Query Intent Detection + Query Expansion
# Covers all 15 NEMHEM corpus documents across 7 domains:
#   swm | environment | citizen_services | health | ai_technology | finance_budget | land_rural | heritage_geography
#
# Two public functions:
#   detect_query_type(query)  → str (query type label)
#   expand_query(query, query_type) → str (query + expanded synonyms)


import re


# ─────────────────────────────────────────────────────────────────────────────
# QUERY TYPE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_query_type(query: str) -> str:
    """
    Classify user query into one of:
        definition | enforcement | table | procedure | eligibility |
        financial | policy_lookup | explanation | general

    Checks are ordered from most-specific to most-generic.
    """
    q = query.lower()

    # ── Definition ────────────────────────────────────────────────────────────
    if any(x in q for x in [
        "define", "definition", "meaning", "what is", "what are",
        "what does", "refers to", "means",
        # Hindi / Marathi
        "काय आहे", "म्हणजे काय", "व्याख्या",
        # Gujarati
        "શું છે", "વ્યાખ્યા", "અર્થ"
    ]):
        return "definition"

    # ── Enforcement / Penalty ─────────────────────────────────────────────────
    if any(x in q for x in [
        "penalty", "fine", "violation", "offence", "non compliance",
        "non-compliance", "punishment", "prosecution", "liable",
        "action taken", "enforcement", "notice", "show cause",
        # Hindi / Marathi
        "दंड", "शिक्षा", "उल्लंघन", "कारवाई",
        # Gujarati
        "દંડ", "સજા", "ઉલ્લંઘન"
    ]):
        return "enforcement"

    # ── Table / Schedule / Numeric ────────────────────────────────────────────
    if any(x in q for x in [
        "table", "schedule", "per day", "per kg", "per month",
        "user charge", "user fee", "charges", "how much", "rate",
        "amount", "kg", "litre", "quota", "limit",
        "property tax rate", "budget allocation", "allocation amount",
        "index value", "AQI value", "PM2.5 level", "PM10 level"
    ]):
        return "table"

    # ── Procedure / How-to ────────────────────────────────────────────────────
    if any(x in q for x in [
        "how to", "process", "procedure", "steps", "step by step",
        "apply", "register", "submit", "obtain", "get", "avail",
        "what to do", "where to go", "whom to contact",
        "application process", "how do i", "how can i",
        # Hindi / Marathi
        "कसे करावे", "प्रक्रिया", "अर्ज कसा", "कुठे जावे",
        # Gujarati
        "કેવી રીતે", "પ્રક્રિયા", "અરજી કેવી રીતે"
    ]):
        return "procedure"

    # ── Eligibility / Criteria ────────────────────────────────────────────────
    if any(x in q for x in [
        "eligible", "eligibility", "who can", "who can apply",
        "criteria", "requirement", "qualification", "who is",
        "can i apply", "am i eligible", "conditions",
        # Hindi / Marathi
        "पात्रता", "कोण पात्र", "अटी", "शर्त",
        # Gujarati
        "પાત્રતા", "કોણ અરજી", "શરત"
    ]):
        return "eligibility"

    # ── Financial ─────────────────────────────────────────────────────────────
    if any(x in q for x in [
        "budget", "fund", "allocation", "expenditure", "revenue",
        "subsidy", "grant", "cost", "financial", "rupee", "crore",
        "lakh", "outlay", "provision", "estimate", "scheme amount",
        "property tax", "water tax",
        # Marathi
        "अर्थसंकल्प", "निधी", "खर्च", "अनुदान"
    ]):
        return "financial"

    # ── Policy Lookup ─────────────────────────────────────────────────────────
    if any(x in q for x in [
        "rule", "rules", "policy", "guideline", "guidelines",
        "act", "law", "bye law", "byelaw", "notification",
        "circular", "order", "resolution", "GR", "government resolution",
        "provision", "as per", "according to", "section", "clause",
        "article", "schedule", "regulation", "mandate",
        # Hindi / Marathi
        "नियम", "धोरण", "अधिसूचना", "शासन निर्णय", "कलम",
        # Gujarati
        "નિયમ", "ધારો", "સૂચના", "જોગવાઈ"
    ]):
        return "policy_lookup"

    # ── Explanation / Why / Impact ────────────────────────────────────────────
    if any(x in q for x in [
        "why", "reason", "impact", "effect", "importance",
        "benefit", "purpose", "objective", "goal", "significance",
        "rationale", "role of", "function of",
        # Hindi / Marathi
        "का", "उद्देश", "महत्त्व", "फायदा",
        # Gujarati
        "કેમ", "ઉદ્દેશ", "મહત્વ", "ફાયદો"
    ]):
        return "explanation"

    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# EXPANSION MAP
# Organized by domain for clarity and maintainability
# ─────────────────────────────────────────────────────────────────────────────

EXPANSION_MAP = {

    # ── Generic governance ────────────────────────────────────────────────────
    "authority":        ["government", "department", "local body", "municipal corporation", "collector"],
    "government":       ["authority", "agency", "ministry", "department"],
    "department":       ["ministry", "authority", "directorate", "commissioner"],
    "citizen":          ["resident", "person", "occupier", "householder", "applicant"],
    "person":           ["citizen", "individual", "occupier", "applicant"],
    "applicant":        ["citizen", "beneficiary", "user", "person"],
    "rules":            ["regulations", "guidelines", "law", "act", "bye law", "byelaw"],
    "regulation":       ["rules", "law", "guideline", "order"],
    "notification":     ["circular", "order", "GR", "gazette", "resolution"],
    "circular":         ["notification", "order", "resolution", "GR"],
    "order":            ["notification", "circular", "direction", "instruction"],
    "guideline":        ["rules", "policy", "framework", "directive", "standard"],
    "policy":           ["guideline", "framework", "scheme", "programme", "plan"],
    "act":              ["law", "legislation", "statute", "rule", "provision"],
    "provision":        ["section", "clause", "rule", "article", "schedule"],
    "section":          ["clause", "article", "provision", "sub-section"],
    "clause":           ["section", "provision", "sub-clause"],
    "schedule":         ["annexure", "appendix", "table", "list"],
    "penalty":          ["fine", "punishment", "violation", "offence", "sanction", "action"],
    "fine":             ["penalty", "violation", "sanction"],
    "violation":        ["offence", "non-compliance", "breach", "penalty"],
    "compliance":       ["adherence", "conformity", "following rules", "implementation"],
    "enforcement":      ["penalty", "fine", "action", "notice", "prosecution"],

    # ── Financial ─────────────────────────────────────────────────────────────
    "charges":          ["fees", "rates", "cost", "levy", "tariff", "user charges", "user fee"],
    "fee":              ["charges", "rates", "cost", "levy"],
    "cost":             ["amount", "charges", "fee", "expenditure"],
    "budget":           ["allocation", "fund", "expenditure", "outlay", "estimate", "provision"],
    "allocation":       ["budget", "fund", "grant", "provision", "outlay"],
    "fund":             ["allocation", "budget", "grant", "outlay"],
    "grant":            ["subsidy", "fund", "allocation", "financial assistance"],
    "subsidy":          ["grant", "benefit", "financial assistance", "incentive"],
    "revenue":          ["income", "receipt", "collection", "fund"],
    "expenditure":      ["spending", "outlay", "cost", "budget"],
    "tax":              ["levy", "cess", "charges", "property tax", "water tax"],

    # ── SWM / Waste ───────────────────────────────────────────────────────────
    "waste":            ["garbage", "refuse", "solid waste", "kachra", "rubbish"],
    "solid waste":      ["garbage", "refuse", "swm", "waste", "municipal waste"],
    "garbage":          ["waste", "refuse", "solid waste", "rubbish"],
    "segregation":      ["separation", "sorting", "categorization", "wet dry separation"],
    "wet waste":        ["bio-degradable", "organic waste", "food waste", "kitchen waste"],
    "dry waste":        ["non bio-degradable", "recyclable", "inert waste", "plastic waste"],
    "hazardous waste":  ["e-waste", "toxic", "biomedical", "chemical waste"],
    "compost":          ["composting", "organic processing", "vermicompost", "bio-gas"],
    "landfill":         ["dumping ground", "sanitary landfill", "disposal site", "dumpsite"],
    "collection":       ["pickup", "gathering", "door-to-door", "transport"],
    "disposal":         ["processing", "treatment", "dumping", "landfill"],
    "segregation":      ["sorting", "separation", "categorization"],
    "generator":        ["bulk generator", "household", "establishment", "producer"],
    "bulk generator":   ["commercial", "residential society", "institution", "generator"],
    "user charge":      ["user fee", "charges", "fee", "rates", "levy"],
    "user fee":         ["user charges", "fee", "charges", "rates"],

    # ── Environment ───────────────────────────────────────────────────────────
    "air quality":      ["AQI", "pollution", "PM2.5", "PM10", "NO2", "SO2", "emission"],
    "AQI":              ["air quality index", "pollution level", "PM2.5", "PM10"],
    "pollution":        ["contamination", "emission", "discharge", "air quality", "water quality"],
    "water quality":    ["water pollution", "contamination", "drinking water", "effluent"],
    "noise":            ["sound", "decibel", "noise pollution", "noise level"],
    "climate":          ["weather", "temperature", "rainfall", "monsoon", "environment"],
    "mangrove":         ["coastal ecosystem", "wetland", "forest", "green cover"],
    "monitoring":       ["surveillance", "measurement", "assessment", "station"],

    # ── Health ────────────────────────────────────────────────────────────────
    "health":           ["medical", "healthcare", "hospital", "clinic", "disease"],
    "hospital":         ["PHC", "CHC", "health centre", "clinic", "dispensary"],
    "PHC":              ["primary health centre", "health centre", "sub-centre", "hospital"],
    "CHC":              ["community health centre", "hospital", "secondary care", "PHC"],
    "doctor":           ["physician", "medical officer", "MO", "specialist", "practitioner"],
    "medicine":         ["drug", "pharmaceutical", "tablet", "injection", "treatment"],
    "disease":          ["illness", "infection", "condition", "ailment"],
    "malaria":          ["vector-borne", "mosquito", "fever", "disease"],
    "TB":               ["tuberculosis", "pulmonary disease", "RNTCP", "NTEP"],
    "HIV":              ["AIDS", "ICTC", "NACO", "blood-borne"],
    "immunization":     ["vaccination", "vaccine", "inoculation", "immunisation"],
    "maternal":         ["pregnancy", "antenatal", "postnatal", "mother", "childbirth"],
    "child health":     ["paediatric", "child care", "infant", "nutrition"],
    "insurance":        ["coverage", "health cover", "scheme", "Ayushman"],
    "Ayushman":         ["Ayushman Bharat", "PMJAY", "health insurance", "health scheme"],

    # ── AI / Technology ───────────────────────────────────────────────────────
    "AI":               ["artificial intelligence", "machine learning", "algorithm", "automation"],
    "artificial intelligence": ["AI", "ML", "deep learning", "algorithm", "automation"],
    "governance":       ["regulation", "framework", "guideline", "oversight", "accountability"],
    "bias":             ["fairness", "discrimination", "prejudice", "algorithmic bias"],
    "transparency":     ["explainability", "accountability", "interpretability", "openness"],
    "data":             ["dataset", "information", "privacy", "personal data", "DPDP"],
    "privacy":          ["data protection", "DPDP", "personal information", "confidentiality"],
    "automation":       ["AI", "machine learning", "robotics", "algorithm", "digitization"],
    "reskilling":       ["upskilling", "training", "learning", "retraining", "capacity building"],
    "upskilling":       ["reskilling", "training", "skill development", "learning"],
    "employment":       ["job", "work", "livelihood", "career", "occupation"],
    "job":              ["employment", "work", "career", "occupation", "livelihood"],
    "internship":       ["fellowship", "training programme", "TIP", "NeGD", "apprenticeship"],
    "digital":          ["online", "e-governance", "technology", "IT", "electronic"],
    "startup":          ["entrepreneur", "innovation", "venture", "company", "MSME"],

    # ── Citizen Services / Portal ─────────────────────────────────────────────
    "certificate":      ["document", "proof", "attestation", "domicile", "caste", "income"],
    "domicile":         ["residence proof", "domicile certificate", "residence certificate"],
    "caste":            ["caste certificate", "SC", "ST", "OBC", "community"],
    "income":           ["income certificate", "earnings", "salary", "financial status"],
    "ration":           ["ration card", "food", "PDS", "public distribution"],
    "7/12":             ["satbara", "land record", "property record", "revenue record"],
    "mutation":         ["name transfer", "property transfer", "record change", "ferfar"],
    "service delivery": ["seva", "public service", "government service", "RTPS"],
    "RTPS":             ["right to public service", "service delivery", "time-bound service"],
    "DBT":              ["direct benefit transfer", "subsidy", "Aaple Sarkar", "portal"],
    "portal":           ["online", "website", "application", "digital service"],
    "apply":            ["application", "register", "submit", "enroll", "avail"],
    "application":      ["apply", "form", "request", "submission"],
    "beneficiary":      ["applicant", "citizen", "eligible person", "recipient"],

    # ── Land / Rural ──────────────────────────────────────────────────────────
    "encroachment":     ["अतिक्रमण", "unauthorized occupation", "illegal construction", "regularization"],
    "regularization":   ["नियमितीकरण", "legalization", "approval", "permission"],
    "government land":  ["sarkari jamin", "shासकीय जमीन", "revenue land", "public land"],
    "rural":            ["village", "gram", "rural area", "grampanchayat", "खेडे"],
    "grampanchayat":    ["village panchayat", "local body", "gram panchayat"],
    "patta":            ["title deed", "land document", "ownership", "property right"],

    # ── Geography / Heritage ──────────────────────────────────────────────────
    "geography":        ["location", "district", "area", "region", "terrain", "topography"],
    "heritage":         ["culture", "history", "tradition", "historical", "cultural"],
    "tribe":            ["tribal", "adivasi", "indigenous", "scheduled tribe"],
    "population":       ["census", "demographics", "residents", "inhabitants"],
    "agriculture":      ["farming", "crops", "land use", "kisan", "farmer"],

    # ── Multilingual hints ────────────────────────────────────────────────────
    # Marathi
    "नागरिक":           ["citizen", "resident", "nagarik", "person"],
    "विल्हेवाट":           ["disposal", "waste disposal", "solid waste disposal"],
    "सॅनिटरी":            ["sanitary", "hygiene"],
    "डायपर":            ["diaper", "sanitary waste"],
    "अर्ज":             ["application", "apply", "form", "request"],
    "नियम":             ["rules", "regulation", "law", "guideline"],
    "दंड":              ["penalty", "fine", "punishment"],
    "योजना":            ["scheme", "programme", "plan", "policy"],
    "प्रमाणपत्र":          ["certificate", "document", "proof"],
    "रक्कम":            ["amount", "charges", "cost", "fee"],
    "आरोग्य":           ["health", "medical", "hospital"],
    "कचरा":             ["waste", "garbage", "solid waste"],
    # Gujarati
    "નિયમ":             ["rules", "regulation", "law"],
    "અરજી":             ["application", "apply", "request"],
    "સેવા":             ["service", "seva", "delivery"],
    "દંડ":              ["penalty", "fine"],
    "આરોગ્ય":           ["health", "medical"],
    "કચરો":             ["waste", "garbage", "solid waste"],
}


# ─────────────────────────────────────────────────────────────────────────────
# INTENT-AWARE EXPANSION TERMS
# Applied on top of word-level expansion based on the detected query_type
# ─────────────────────────────────────────────────────────────────────────────

INTENT_EXPANSION = {

    "table": [
        "schedule", "user fee", "user charges", "rates", "fees",
        "property tax", "amount", "tariff", "table", "list",
        "per kg", "per day", "per month", "per litre",
        "AQI", "PM2.5", "PM10", "index", "budget allocation"
    ],

    "enforcement": [
        "penalty", "fine", "violation", "offence", "non-compliance",
        "sanction", "notice", "prosecution", "action", "liable",
        "legal action", "show cause"
    ],

    "definition": [
        "means", "defined as", "refers to", "includes", "definition",
        "interpretation", "nomenclature", "term", "meaning"
    ],

    "procedure": [
        "step", "process", "how to", "apply", "register",
        "submit", "form", "document required", "where to submit",
        "whom to contact", "time limit", "deadline", "SLA",
        "application process", "portal link", "helpline"
    ],

    "eligibility": [
        "eligible", "who can", "criteria", "condition",
        "requirement", "qualification", "entitled", "beneficiary",
        "income limit", "age limit", "category"
    ],

    "financial": [
        "rupees", "crore", "lakh", "budget", "allocation",
        "expenditure", "outlay", "provision", "estimate",
        "fund", "grant", "subsidy", "tax", "revenue",
        "user charges", "fees"
    ],

    "policy_lookup": [
        "section", "clause", "rule", "article", "schedule",
        "provision provision", "as per", "according to",
        "GR number", "notification number", "circular number",
        "date of notification", "enforcement date"
    ],

    "explanation": [
        "why", "reason", "purpose", "objective", "goal",
        "benefit", "impact", "importance", "rationale",
        "significance", "background", "context"
    ],

    "general": [],  # no extra terms for general
}


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN-SPECIFIC EXPANSION BOOSTERS
# When query clearly targets a domain, inject domain-specific vocabulary
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_BOOSTERS = {

    "swm": [
        "solid waste", "swm", "segregation", "wet waste", "dry waste",
        "bulk generator", "user charges", "compost", "landfill",
        "collection", "disposal", "processing", "bye law", "schedule"
    ],

    "environment": [
        "AQI", "PM2.5", "PM10", "NO2", "air quality", "water quality",
        "noise", "pollution", "monitoring station", "MPCB", "CPCB",
        "mangrove", "green cover", "climate"
    ],

    "citizen_services": [
        "certificate", "domicile", "service delivery", "SLA", "time limit",
        "application", "portal", "online", "RTPS", "DBT", "Aaple Sarkar",
        "grievance", "helpline", "designated officer"
    ],

    "health": [
        "PHC", "CHC", "hospital", "doctor", "medicine", "vacancy",
        "maternal", "immunization", "tuberculosis", "malaria", "HIV",
        "Ayushman", "health insurance", "health policy"
    ],

    "ai_technology": [
        "AI", "artificial intelligence", "machine learning", "algorithm",
        "governance", "bias", "transparency", "privacy", "data protection",
        "reskilling", "employment", "job creation", "internship", "NeGD"
    ],

    "finance_budget": [
        "budget", "allocation", "expenditure", "revenue", "fund",
        "crore", "lakh", "property tax", "water tax", "grant"
    ],

    "land_rural": [
        "encroachment", "regularization", "government land", "patta",
        "grampanchayat", "rural area", "7/12", "satbara", "GR"
    ],

    "heritage_geography": [
        "geography", "history", "culture", "heritage", "tribe",
        "population", "census", "river", "forest", "agriculture"
    ],
}

# Domain detection keywords (same set used in document_router for consistency)
_DOMAIN_DETECT = {
    "swm":              ["solid waste", "swm", "garbage", "waste", "segregation", "compost", "landfill", "kachra", "कचरा", "घनकचरा", "bye law", "byelaw", "mcgm", "bmc","विल्हेवाट", "घनकचरा", "सॅनिटरी", "डायपर"],
    "environment":      ["environment", "air quality", "aqi", "pollution", "pm2.5", "pm10", "noise", "mangrove", "mpcb", "cpcb"],
    "citizen_services": ["certificate", "domicile", "ration", "service delivery", "rtps", "dbt", "aaple sarkar", "nagarik", "सेवा", "अर्ज", "નાગરિક", "સેવા"],
    "health":           ["health", "hospital", "doctor", "phc", "chc", "medicine", "malaria", "tb", "hiv", "maternal", "ayushman"],
    "ai_technology":    ["ai", "artificial intelligence", "machine learning", "meity", "niti aayog", "reskilling", "internship", "negd", "india ai"],
    "finance_budget":   ["budget", "allocation", "expenditure", "crore", "lakh", "property tax", "अर्थसंकल्प", "निधी"],
    "land_rural":       ["gram vikas", "encroachment", "regularization", "grampanchayat", "ग्राम विकास", "अतिक्रमण"],
    "heritage_geography":["valsad heritage", "valsad geography", "valsad culture", "dang", "tribal valsad"],
}


def _detect_domain(query: str) -> str:
    """Detect which document domain the query most likely targets."""
    q = query.lower()
    for domain, triggers in _DOMAIN_DETECT.items():
        if any(t in q for t in triggers):
            return domain
    return "general"


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def expand_query(query: str, query_type: str) -> str:
    """
    Expand query with synonyms and domain/intent-aware booster terms.

    Strategy:
      1. Word-level expansion from EXPANSION_MAP (synonym injection)
      2. Intent-level expansion from INTENT_EXPANSION (query_type boosters)
      3. Domain-level expansion from DOMAIN_BOOSTERS (topic vocabulary)

    Returns original query + space-separated expanded terms.
    Duplicate terms are removed. Original query is always preserved.
    """

    words = re.findall(r"\b\w+\b", query.lower())
    expanded_terms: set = set()

    # ── 1. Word-level synonym expansion ──────────────────────────────────────
    for word in words:
        if word in EXPANSION_MAP:
            expanded_terms.update(EXPANSION_MAP[word])

    # Also check bigrams (two consecutive words)
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    for bigram in bigrams:
        if bigram in EXPANSION_MAP:
            expanded_terms.update(EXPANSION_MAP[bigram])

    # ── 2. Intent-level expansion ─────────────────────────────────────────────
    intent_terms = INTENT_EXPANSION.get(query_type, [])
    expanded_terms.update(intent_terms)

    # ── 3. Domain-level expansion ─────────────────────────────────────────────
    domain = _detect_domain(query)
    if domain != "general":
        domain_terms = DOMAIN_BOOSTERS.get(domain, [])
        expanded_terms.update(domain_terms)

    # ── Compose final query ───────────────────────────────────────────────────
    # Remove terms already present in original query to avoid redundancy
    original_lower = query.lower()
    filtered_terms = {t for t in expanded_terms if t.lower() not in original_lower}

    if filtered_terms:
        expanded_query = query + " " + " ".join(sorted(filtered_terms))
    else:
        expanded_query = query

    return expanded_query.strip()