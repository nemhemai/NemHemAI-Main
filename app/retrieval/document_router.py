# Generic document type classification keywords
# app/retrieval/document_router.py
"""
DOC_TYPE_MAP = {
    "byelaw": ["bye", "byelaw", "by-law"],
    "rules": ["rules", "regulation"],
    "report": ["report", "status"],
    "policy": ["policy", "guideline"],
}

def route_documents(query: str, query_type: str) -> list[str]:
    
    #Returns document type preferences (not file names).

    q = query.lower()

    # 🎯 TABLE / CHARGES → mostly bye-laws / schedules
    if query_type == "table" or any(x in q for x in ["charges", "fees", "rates", "schedule"]):
        return ["byelaw"]

    # ⚖️ PENALTY → bye-laws + rules
    if query_type == "enforcement":
        return ["byelaw", "rules"]

    # 📘 DEFINITIONS → rules
    if query_type == "definition":
        return ["rules"]

    # DEFAULT
    return []

def get_doc_type(document_name: str) -> str:
    doc = (document_name or "").lower()

    for doc_type, keywords in DOC_TYPE_MAP.items():
        if any(k in doc for k in keywords):
            return doc_type

    return "other"
    """

# app/retrieval/document_router.py
#
# Document routing for all 15 NEMHEM corpus documents.
#  
# Documents:
#  1.  swm_rules_2016_central          → SWM Rules 2016 (Central)
#  2.  bmc_swm_bye_laws                → BMC SWM Bye Laws
#  3.  maharashtra_swm_policy          → Maharashtra SWM Policy
#  4.  BMC_Environment_Status_Report   → BMC Environment Status Report 2024-25
#  5.  Citizen_Charter_Nagpur          → Citizen's Charter Nagpur
#  6.  PMC_Budget                      → PMC Budget 2026-27
#  7.  Mah_Gram_Vikas                  → Maharashtra Gram Vikas (Rural Land)
#  8.  Public_Health_Department_GoM    → Maharashtra Public Health Dept Report
#  9.  Ministry_of_Health_GoI          → National Health Policy 2017
# 10.  India_AI_Governance_Guidelines  → MeitY AI Governance Guidelines
# 11.  Roadmap_for_Job_Creation_AI     → NITI Aayog AI Jobs Roadmap
# 12.  Updated-Winter-Announcement     → NeGD Technical Internship 2025
# 13.  Aaple-Sarkar-DBT-Portal         → Aaple Sarkar DBT Portal Help File
# 14.  Goverment_Service_Delivery_GJ   → Gujarat RTPS Notification (Valsad)
# 15.  Social_Geographical_Valsad      → Valsad District Heritage Report


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT REGISTRY
# Each key is a stable doc_key. Values carry metadata used for routing logic.
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENT_REGISTRY = {

    # ── Solid Waste Management ────────────────────────────────────────────────

    "swm_rules_2016_central": {
        "title": "Solid Waste Management Rules 2016",
        "doc_type": "rules",
        "domain": "swm",
        "jurisdiction": "central",
        "state": None,
        "language": "en",
        "department_code": "MOEFCC",
        "keywords": [
            "solid waste", "swm rules", "swm 2016", "central rules",
            "schedule", "compost", "landfill", "segregation", "bio-degradable",
            "non bio-degradable", "generator", "bulk generator", "processing",
            "sanitary landfill", "MOEFCC", "environment", "collection",
            "disposal", "penalty", "fine", "user fee", "user charges"
        ],
    },

    "bmc_swm_bye_laws": {
        "title": "BMC Solid Waste Management Bye Laws 2019",
        "doc_type": "byelaw",
        "domain": "swm",
        "jurisdiction": "municipal",
        "state": "Maharashtra",
        "language": "en",
        "department_code": "MCGM",
        "keywords": [
            "bmc", "mcgm", "mumbai", "bye law", "byelaw", "by-law",
            "solid waste", "swm", "segregation", "wet waste", "dry waste",
            "hazardous waste", "user charges", "fees", "penalty", "fine",
            "composting", "bulk generator", "rwa", "society", "builder",
            "non compliance", "non-compliance", "collection", "vehicle",
            "occupier", "property", "enforcement"
        ],
    },

    "maharashtra_swm_policy": {
        "title": "Maharashtra Solid Waste Management Policy 2018",
        "doc_type": "policy",
        "domain": "swm",
        "jurisdiction": "state",
        "state": "Maharashtra",
        "language": "mr",
        "department_code": "UDD",
        "keywords": [
            "maharashtra swm policy", "solid waste", "UDD", "urban development",
            "municipal", "waste management", "segregation", "compost",
            "landfill", "decentralized", "cluster", "nagar parishad",
            "nagar panchayat", "grampanchayat", "waste to energy",
            "secondary collection", "transfer station", "implementation"
        ],
    },

    # ── Environment ───────────────────────────────────────────────────────────

    "BMC_Environment_Status_Report": {
        "title": "BMC Environment Status Report 2024-25",
        "doc_type": "report",
        "domain": "environment",
        "jurisdiction": "municipal",
        "state": "Maharashtra",
        "language": "en",
        "department_code": "BMC-ENV",
        "keywords": [
            "BMC", "environment", "air quality", "water quality", "noise",
            "AQI", "PM2.5", "PM10", "NO2", "SO2", "CO", "pollution",
            "mumbai", "climate", "green cover", "tree", "mangrove",
            "solid waste", "sea", "creek", "rain", "flood", "drainage",
            "groundwater", "ESR", "environmental status", "monitoring",
            "CPCB", "MPCB", "station", "index"
        ],
    },

    # ── Citizens / Services ───────────────────────────────────────────────────

    "Citizen_Charter_Nagpur": {
        "title": "Citizen's Charter – District Collector Office, Nagpur",
        "doc_type": "charter",
        "domain": "citizen_services",
        "jurisdiction": "municipal",
        "state": "Maharashtra",
        "language": "mr",
        "department_code": "REV-MAHA-NAG",
        "keywords": [
            "citizen charter", "nagpur", "collector", "district",
            "service delivery", "nagarik seva", "seva", "certificate",
            "revenue", "7/12", "satbara", "mutation", "domicile",
            "income certificate", "caste certificate", "ration card",
            "complaint", "grievance", "time limit", "deadline", "SLA",
            "nagarik", "अर्ज", "प्रमाणपत्र", "नागरिक सेवा", "तक्रार"
        ],
    },

    "Aaple_Sarkar_DBT_Portal": {
        "title": "Aaple Sarkar DBT Portal User Guidelines and Help File",
        "doc_type": "manual",
        "domain": "citizen_services",
        "jurisdiction": "state",
        "state": "Maharashtra",
        "language": "en",
        "department_code": "MAHA-IT",
        "keywords": [
            "aaple sarkar", "DBT", "direct benefit transfer", "portal",
            "online", "application", "registration", "login", "password",
            "scheme", "beneficiary", "bank account", "aadhar", "aadhaar",
            "OTP", "subsidy", "benefit", "farmer", "student", "upload",
            "document", "status", "track", "how to apply", "apply online",
            "digital", "e-service", "maharashtra portal"
        ],
    },

    # ── Budget / Finance ──────────────────────────────────────────────────────

    "PMC_Budget": {
        "title": "Pune Municipal Corporation Budget 2026-27",
        "doc_type": "budget",
        "domain": "finance",
        "jurisdiction": "municipal",
        "state": "Maharashtra",
        "language": "mr",
        "department_code": "PMC-FIN",
        "keywords": [
            "PMC", "pune", "budget", "allocation", "expenditure",
            "revenue", "capital", "grant", "fund", "scheme",
            "property tax", "water tax", "infrastructure", "road",
            "hospital", "school", "drainage", "garden", "ward",
            "crore", "lakh", "provision", "estimate", "अर्थसंकल्प",
            "महानगरपालिका", "पुणे", "निधी", "खर्च", "उत्पन्न"
        ],
    },

    # ── Rural Development / Land ──────────────────────────────────────────────

    "Mah_Gram_Vikas": {
        "title": "Policy Amendment – Regularization of Residential Encroachments on Government Land (Rural Maharashtra)",
        "doc_type": "circular",
        "domain": "land_revenue",
        "jurisdiction": "state",
        "state": "Maharashtra",
        "language": "mr",
        "department_code": "MAHA-RDD",
        "keywords": [
            "gram vikas", "rural", "encroachment", "sarkari jamin",
            "government land", "regularization", "residential", "rural area",
            "grampanchayat", "village", "patta", "plot", "survey number",
            "7/12", "satbara", "revenue", "mutation", "ग्राम विकास",
            "अतिक्रमण", "नियमितीकरण", "शासकीय जमीन", "ग्रामीण",
            "पट्टा", "योजना", "circular", "GR", "शासन निर्णय"
        ],
    },

    # ── Health ────────────────────────────────────────────────────────────────

    "Public_Health_Department_GoM": {
        "title": "Maharashtra Public Health Department Comprehensive Note – 1st Session 2025",
        "doc_type": "report",
        "domain": "health",
        "jurisdiction": "state",
        "state": "Maharashtra",
        "language": "en",
        "department_code": "PHD-MAHA",
        "keywords": [
            "public health", "maharashtra health", "hospital", "PHC",
            "primary health centre", "CHC", "district hospital", "sub-centre",
            "doctor", "nurse", "ANM", "ASHA", "vacancy", "budget health",
            "maternal", "child health", "immunization", "malaria", "TB",
            "tuberculosis", "HIV", "medicine", "drug", "equipment",
            "Ayushman", "Mahatma Phule", "health insurance", "session 2025"
        ],
    },

    "Ministry_of_Health_GoI": {
        "title": "National Health Policy 2017",
        "doc_type": "policy",
        "domain": "health",
        "jurisdiction": "central",
        "state": None,
        "language": "en",
        "department_code": "MoHFW",
        "keywords": [
            "national health policy", "NHP 2017", "MoHFW", "health policy",
            "universal health coverage", "UHC", "primary care", "tertiary care",
            "AYUSH", "nutrition", "disease burden", "NCD", "communicable",
            "mental health", "digital health", "health financing",
            "out of pocket", "GDPNDP expenditure", "health workforce",
            "essential medicines", "Jan Aushadhi", "Ayushman Bharat",
            "goal", "target", "indicator", "2025"
        ],
    },

    # ── AI / Technology ───────────────────────────────────────────────────────

    "India_AI_Governance_Guidelines": {
        "title": "India AI Governance Guidelines 2025 – MeitY",
        "doc_type": "guideline",
        "domain": "ai_technology",
        "jurisdiction": "central",
        "state": None,
        "language": "en",
        "department_code": "MeitY-INDIAAI",
        "keywords": [
            "AI governance", "artificial intelligence", "MeitY", "IndiaAI",
            "responsible AI", "trustworthy AI", "ethical AI", "bias",
            "fairness", "transparency", "accountability", "explainability",
            "data privacy", "safety", "risk", "compliance", "framework",
            "regulation", "guideline", "2025", "LLM", "foundation model",
            "algorithm", "deepfake", "automated decision", "DPDP"
        ],
    },

    "Roadmap_for_Job_Creation_AI": {
        "title": "Roadmap for Job Creation in the AI Economy – NITI Aayog 2025",
        "doc_type": "report",
        "domain": "ai_technology",
        "jurisdiction": "central",
        "state": None,
        "language": "en",
        "department_code": "NITI-FTH",
        "keywords": [
            "AI economy", "job creation", "NITI Aayog", "employment",
            "reskilling", "upskilling", "future of work", "automation",
            "workforce", "skill", "training", "platform economy",
            "gig worker", "digital economy", "startup", "innovation",
            "industry 4.0", "human capital", "GDP", "productivity",
            "labour market", "occupation", "career", "education", "STEM"
        ],
    },

    "Updated_Winter_Announcement_2025": {
        "title": "NeGD Technical Internship Programme 2025 Announcement",
        "doc_type": "announcement",
        "domain": "ai_technology",
        "jurisdiction": "central",
        "state": None,
        "language": "en",
        "department_code": "MeitY",
        "keywords": [
            "internship", "NeGD", "Digital India", "technical internship",
            "programme", "2025", "winter", "application", "eligibility",
            "stipend", "duration", "selection", "student", "engineering",
            "MeitY", "government internship", "how to apply", "last date",
            "registration", "fellowship", "technology"
        ],
    },

    # ── Gujarat Documents ─────────────────────────────────────────────────────

    "Goverment_Service_Delivery_GJ": {
        "title": "Government Service Delivery Notification under RTPS Act – Valsad, Gujarat",
        "doc_type": "notification",
        "domain": "citizen_services",
        "jurisdiction": "district",
        "state": "Gujarat",
        "language": "gu",
        "department_code": "GJ-RTPS",
        "keywords": [
            "RTPS", "right to public service", "service delivery",
            "Valsad", "Gujarat", "notification", "seva", "time limit",
            "deadline", "designated officer", "first appeal", "second appeal",
            "certificate", "licence", "permission", "application",
            "સેવા", "અરજી", "સમય મર્યાદા", "અધિકારી", "ફરિયાદ",
            "વલસાડ", "ગુજરાત", "RTPS"
        ],
    },

    "Social_Geographical_Valsad": {
        "title": "Social, Geographical and Cultural Heritage of Valsad District",
        "doc_type": "report",
        "domain": "heritage_geography",
        "jurisdiction": "district",
        "state": "Gujarat",
        "language": "gu",
        "department_code": "GJ-DIST-VALSAD",
        "keywords": [
            "Valsad", "valsad district", "Gujarat", "geography", "culture",
            "heritage", "history", "population", "tribe", "tribal",
            "river", "forest", "agriculture", "economy", "dang",
            "surat", "coastal", "social", "literacy", "census",
            "વલસાડ", "ભૂગોળ", "સંસ્કૃતિ", "ઈતિહાસ", "વસ્તી",
            "આદિવાસી", "નદી", "ખેતી", "જિલ્લો"
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# DOC TYPE MAP  (for get_doc_type — matches document filenames/names)
# ─────────────────────────────────────────────────────────────────────────────

DOC_TYPE_MAP = {
    "byelaw":       ["bye", "byelaw", "by-law", "bye_law"],
    "rules":        ["rules", "rule", "regulation", "swm_rules"],
    "policy":       ["policy", "guideline", "guidelines", "niti"],
    "report":       ["report", "status", "esr", "roadmap", "comprehensive"],
    "charter":      ["charter", "citizen_charter"],
    "budget":       ["budget"],
    "circular":     ["circular", "gram_vikas", "gram vikas"],
    "manual":       ["manual", "help", "dbt", "portal", "aaple"],
    "notification": ["notification", "rtps", "service_delivery"],
    "announcement": ["announcement", "internship", "winter"],
}


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN → DOC TYPES PREFERENCE TABLE
# Used by route_documents() to prefer certain doc types for a query type
# ─────────────────────────────────────────────────────────────────────────────

QUERY_TYPE_TO_DOC_TYPES = {
    "definition":   ["rules", "byelaw", "policy", "guideline"],
    "enforcement":  ["byelaw", "rules", "notification", "circular"],
    "table":        ["byelaw", "budget", "rules"],
    "procedure":    ["manual", "charter", "notification", "circular"],
    "eligibility":  ["manual", "charter", "notification", "announcement"],
    "financial":    ["budget", "byelaw", "rules"],
    "policy_lookup":["policy", "circular", "rules", "guideline"],
    "explanation":  ["report", "policy", "guideline"],
    "general":      [],  # no preference → search all
}


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN KEYWORD → DOC KEYS
# Fast lookup: if query clearly targets a domain, short-list to those doc keys
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_TRIGGERS = {

    "swm": {
        "keywords": [
            "solid waste", "swm", "garbage", "waste", "segregation",
            "compost", "landfill", "refuse", "dry waste", "wet waste",
            "bulk generator", "user charges", "bmc bye", "bye law",
            "waste management", "kachra", "कचरा", "घनकचरा"
        ],
        "doc_keys": [
            "swm_rules_2016_central",
            "bmc_swm_bye_laws",
            "maharashtra_swm_policy",
            "BMC_Environment_Status_Report",
        ],
    },

    "environment": {
        "keywords": [
            "environment", "air quality", "AQI", "pollution", "PM2.5",
            "PM10", "NO2", "noise", "water quality", "climate", "mangrove",
            "green cover", "MPCB", "CPCB", "emission", "monitoring"
        ],
        "doc_keys": [
            "BMC_Environment_Status_Report",
            "swm_rules_2016_central",
            "maharashtra_swm_policy",
        ],
    },

    "citizen_services": {
        "keywords": [
            "certificate", "domicile", "income certificate", "caste",
            "ration", "7/12", "satbara", "mutation", "service delivery",
            "RTPS", "citizen", "nagarik", "nagarik seva", "aaple sarkar",
            "DBT", "subsidy", "apply", "application", "portal",
            "नागरिक", "अर्ज", "प्रमाणपत्र", "સેવા", "અરજી"
        ],
        "doc_keys": [
            "Citizen_Charter_Nagpur",
            "Aaple_Sarkar_DBT_Portal",
            "Goverment_Service_Delivery_GJ",
        ],
    },

    "health": {
        "keywords": [
            "health", "hospital", "doctor", "PHC", "CHC", "medicine",
            "patient", "disease", "malaria", "TB", "HIV", "maternal",
            "child health", "immunization", "vaccine", "health policy",
            "ayushman", "insurance", "health budget", "nurse", "ASHA"
        ],
        "doc_keys": [
            "Public_Health_Department_GoM",
            "Ministry_of_Health_GoI",
        ],
    },

    "ai_technology": {
        "keywords": [
            "AI", "artificial intelligence", "machine learning", "deep learning",
            "LLM", "algorithm", "digital", "MeitY", "NITI Aayog",
            "governance AI", "responsible AI", "bias AI", "automation",
            "reskilling", "job AI", "employment technology", "internship",
            "NeGD", "India AI", "AI policy", "AI regulation"
        ],
        "doc_keys": [
            "India_AI_Governance_Guidelines",
            "Roadmap_for_Job_Creation_AI",
            "Updated_Winter_Announcement_2025",
        ],
    },

    "finance_budget": {
        "keywords": [
            "budget", "allocation", "expenditure", "revenue", "fund",
            "crore", "lakh", "grant", "capital", "property tax",
            "water tax", "अर्थसंकल्प", "निधी", "खर्च", "उत्पन्न"
        ],
        "doc_keys": [
            "PMC_Budget",
        ],
    },

    "land_rural": {
        "keywords": [
            "gram vikas", "rural", "encroachment", "government land",
            "regularization", "grampanchayat", "village land", "patta",
            "ग्राम विकास", "अतिक्रमण", "नियमितीकरण", "शासकीय जमीन",
            "ग्रामीण", "GR", "शासन निर्णय"
        ],
        "doc_keys": [
            "Mah_Gram_Vikas",
        ],
    },

    "gujarat": {
        "keywords": [
            "gujarat", "valsad", "RTPS", "Gujarat service",
            "gu", "gujarati", "ગુજરાત", "વલસાડ", "RTPS"
        ],
        "doc_keys": [
            "Goverment_Service_Delivery_GJ",
            "Social_Geographical_Valsad",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def get_doc_type(document_name: str) -> str:
    """
    Infer doc_type from a document filename or title string.
    Falls back to 'other' if no match.
    """
    doc = (document_name or "").lower()
    for doc_type, keywords in DOC_TYPE_MAP.items():
        if any(k in doc for k in keywords):
            return doc_type
    return "other"


def route_documents(query: str, query_type: str) -> list:
    """
    Returns an ordered list of preferred doc_type strings AND/OR doc_keys
    based on the query text and query_type classification.

    Return value is consumed by the retriever to boost matching chunks.
    Two keys are returned:
        "preferred_doc_types" → list of doc_type strings  (boost by type)
        "preferred_doc_keys"  → list of specific doc keys (boost by document)

    For backward-compatibility this function still returns a flat list of
    doc_type strings (same as before). The retriever can call
    route_documents_full() to get the richer dict.
    """
    result = route_documents_full(query, query_type)
    return result["preferred_doc_types"]


def route_documents_full(query: str, query_type: str) -> dict:
    """
    Full routing result with both preferred doc types and specific doc keys.

    Returns:
        {
            "preferred_doc_types": [...],   # e.g. ["byelaw", "rules"]
            "preferred_doc_keys":  [...],   # e.g. ["bmc_swm_bye_laws", ...]
        }
    """
    q = query.lower()

    preferred_doc_types: list = []
    preferred_doc_keys:  list = []

    # ── Step 1: Domain detection from query text ──────────────────────────────
    matched_domains = []
    for domain, cfg in DOMAIN_TRIGGERS.items():
        if any(kw.lower() in q for kw in cfg["keywords"]):
            matched_domains.append(domain)
            preferred_doc_keys.extend(cfg["doc_keys"])

    # ── Step 2: Query-type → doc type preference ──────────────────────────────
    preferred_doc_types = QUERY_TYPE_TO_DOC_TYPES.get(query_type, [])

    # ── Step 3: Jurisdiction / language overrides ─────────────────────────────

    # Gujarati script in query → strongly prefer Gujarat documents
    import re
    if re.search(r"[\u0A80-\u0AFF]", query):
        for key in ["Goverment_Service_Delivery_GJ", "Social_Geographical_Valsad"]:
            if key not in preferred_doc_keys:
                preferred_doc_keys.insert(0, key)

    # Marathi / Devanagari in query → prefer Maharashtra documents first
    if re.search(r"[\u0900-\u097F]", query):
        marathi_keys = [
            "Citizen_Charter_Nagpur",
            "maharashtra_swm_policy",
            "Mah_Gram_Vikas",
            "PMC_Budget",
            "Public_Health_Department_GoM",
        ]
        for key in marathi_keys:
            if key not in preferred_doc_keys:
                preferred_doc_keys.append(key)

    # ── Step 4: Specific keyword overrides (high-confidence direct routing) ───

    # Bye-law charges / fees → BMC bye laws first
    if any(x in q for x in ["user charge", "user fee", "bye law", "byelaw", "by-law", "mcgm", "bmc rule"]):
        _prepend_if_absent(preferred_doc_keys, "bmc_swm_bye_laws")
        _prepend_if_absent(preferred_doc_types, "byelaw")

    # Central SWM rules → swm_rules_2016_central
    if any(x in q for x in ["swm rules 2016", "solid waste management rules", "central rules", "schedule ii", "schedule i"]):
        _prepend_if_absent(preferred_doc_keys, "swm_rules_2016_central")

    # PMC budget specific
    if any(x in q for x in ["pune budget", "pmc budget", "pmc allocation", "pune municipal budget"]):
        _prepend_if_absent(preferred_doc_keys, "PMC_Budget")
        _prepend_if_absent(preferred_doc_types, "budget")

    # Health policy central
    if any(x in q for x in ["national health policy", "nhp 2017", "mohfw"]):
        _prepend_if_absent(preferred_doc_keys, "Ministry_of_Health_GoI")

    # Maharashtra health
    if any(x in q for x in ["maharashtra health", "phd maha", "session 2025 health", "maharashtra hospital"]):
        _prepend_if_absent(preferred_doc_keys, "Public_Health_Department_GoM")

    # AI governance
    if any(x in q for x in ["ai governance", "meity ai", "india ai", "responsible ai", "trusted ai", "ai guidelines"]):
        _prepend_if_absent(preferred_doc_keys, "India_AI_Governance_Guidelines")
        _prepend_if_absent(preferred_doc_types, "guideline")

    # AI jobs / reskilling
    if any(x in q for x in ["ai jobs", "ai economy", "job creation ai", "reskilling", "niti aayog ai"]):
        _prepend_if_absent(preferred_doc_keys, "Roadmap_for_Job_Creation_AI")

    # Internship NeGD
    if any(x in q for x in ["negd internship", "digital india internship", "technical internship", "tip 2025", "winter 2025"]):
        _prepend_if_absent(preferred_doc_keys, "Updated_Winter_Announcement_2025")
        _prepend_if_absent(preferred_doc_types, "announcement")

    # DBT / Aaple Sarkar portal
    if any(x in q for x in ["aaple sarkar", "dbt portal", "direct benefit", "maharashtra portal", "online apply scheme"]):
        _prepend_if_absent(preferred_doc_keys, "Aaple_Sarkar_DBT_Portal")
        _prepend_if_absent(preferred_doc_types, "manual")

    # Citizen charter Nagpur
    if any(x in q for x in ["citizen charter", "nagpur collector", "nagpur service", "nagarik seva nagpur"]):
        _prepend_if_absent(preferred_doc_keys, "Citizen_Charter_Nagpur")
        _prepend_if_absent(preferred_doc_types, "charter")

    # Gram Vikas / encroachment
    if any(x in q for x in ["gram vikas", "rural encroachment", "regularization land", "government land rural", "ग्राम विकास", "अतिक्रमण"]):
        _prepend_if_absent(preferred_doc_keys, "Mah_Gram_Vikas")
        _prepend_if_absent(preferred_doc_types, "circular")

    # RTPS Gujarat / Valsad service
    if any(x in q for x in ["rtps", "valsad service", "gujarat service delivery", "right to public service"]):
        _prepend_if_absent(preferred_doc_keys, "Goverment_Service_Delivery_GJ")
        _prepend_if_absent(preferred_doc_types, "notification")

    # Valsad geography / heritage
    if any(x in q for x in ["valsad district", "valsad heritage", "valsad geography", "valsad culture", "dang"]):
        _prepend_if_absent(preferred_doc_keys, "Social_Geographical_Valsad")

    # BMC environment report
    if any(x in q for x in ["bmc environment", "bmc air", "mumbai aqi", "mumbai pollution", "bmc esr"]):
        _prepend_if_absent(preferred_doc_keys, "BMC_Environment_Status_Report")
        _prepend_if_absent(preferred_doc_types, "report")

    # Deduplicate while preserving order
    preferred_doc_keys  = _dedupe(preferred_doc_keys)
    preferred_doc_types = _dedupe(preferred_doc_types)

    return {
        "preferred_doc_types": preferred_doc_types,
        "preferred_doc_keys":  preferred_doc_keys,
    }


def get_document_metadata(doc_key: str) -> dict:
    """
    Return full metadata for a registered document key.
    Returns empty dict if not found.
    """
    return DOCUMENT_REGISTRY.get(doc_key, {})


def list_all_doc_keys() -> list:
    """Return all 15 registered document keys."""
    return list(DOCUMENT_REGISTRY.keys())


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _prepend_if_absent(lst: list, item: str) -> None:
    """Insert item at front of list only if not already present."""
    if item not in lst:
        lst.insert(0, item)


def _dedupe(lst: list) -> list:
    """Remove duplicates from a list while preserving insertion order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result