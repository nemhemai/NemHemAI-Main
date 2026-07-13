import json
import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

from app.agents.entitlement.core.entitlement_context import FIELD_DOCUMENTS, check_edge_cases
from app.agents.entitlement.core.entitlement_graph import match_entitlement_graph
from app.agents.entitlement.core.entitlement_memory import remember_entitlement_result
from app.core.database import get_db_conn, release_db_conn
from app.retrieval.entitlement import retrieve_entitlement_clauses
from app.agents.entitlement.services.benefit_optimization_service import optimize_benefits
from app.services.audit_service import log_entitlement_audit
logger = logging.getLogger(__name__)


FIELD_LABELS = {
    "income_annual": "Annual income",
    "land_ownership_acres": "Land Ownership Information",
    "category": "Applicant category",
    "state": "State",
    "urban_rural": "Urban or rural location",
    "education_level": "Education level",
    "occupation": "Occupation",
    "age": "Age",
    "has_aadhaar": "Aadhaar Status",
    "has_bank_account": "Bank Account Details",
    "has_vending_certificate": "Vending certificate",
    "has_ulb_recommendation": "ULB/TVC recommendation letter",
    "has_pucca_house": "Pucca House Ownership Status",
    "is_govt_employee": "Government employee status",
    "pays_income_tax": "Income tax payer status",
    "owns_motorized_vehicle": "Motorized vehicle ownership",
    "is_institutional_landholder": "Institutional landholder status",
    "has_pan": "PAN Card Status",
    "has_passport": "Passport Status",
}


FIELD_VERIFY_STEPS = {
    "has_aadhaar": [
        "Check the Aadhaar card or Aadhaar number with the applicant.",
        "Verify Aadhaar seeding/status on the relevant scheme portal or with the local officer.",
        "If seeding is incomplete, update/link Aadhaar before final scheme approval.",
    ],
    "has_bank_account": [
        "Ask for the applicant's bank passbook, cancelled cheque, or account details.",
        "Confirm that the account is active and belongs to the applicant.",
        "Verify whether the bank account is linked where the scheme requires direct benefit transfer.",
    ],
    "land_ownership_acres": [
        "Ask for land records, 7/12 extract, pattadar passbook, or local land ownership proof.",
        "Confirm that the land is cultivable and linked to the applicant or family where required.",
    ],
    "income_annual": [
        "Ask for a current income certificate or accepted income proof.",
        "Compare the verified amount with the scheme income threshold.",
    ],
    "has_vending_certificate": [
        "Ask for the Certificate of Vending or identity card issued by the ULB/TVC.",
        "If unavailable, check whether a ULB/TVC recommendation letter can be issued.",
    ],
    "has_pan": [
        "Ask for a copy of the PAN card.",
        "Verify that it is linked to Aadhaar if required.",
    ],
    "has_passport": [
        "Ask for a valid Passport.",
    ],
}

FIELD_WHY_REQUIRED = {
    "has_aadhaar": "Aadhaar is required to verify identity and, for schemes like PM-KISAN, to support seeded benefit transfer checks.",
    "has_bank_account": "Bank account details are required because benefits or loans are usually transferred directly to the applicant.",
    "land_ownership_acres": "Land ownership/cultivable land proof is required for farmer schemes that depend on landholding status.",
    "income_annual": "Income is required to check whether the applicant falls within the scheme's income threshold.",
    "category": "Applicant category is required where benefits depend on SC, ST, OBC, or General category rules.",
    "has_vending_certificate": "A vending certificate or ULB/TVC recommendation is required to verify street vendor status.",
    "has_pucca_house": "Pucca house ownership is required for housing schemes that exclude households already owning a pucca house.",
    "has_pan": "PAN is required for financial or loan schemes to check credit history and taxation.",
    "has_passport": "Passport is required for certain education loan portals and international scholarship eligibility.",
}


@dataclass(frozen=True)
class SchemeRule:
    scheme_name: str
    category: str
    keywords: tuple[str, ...]
    required_profile_fields: tuple[str, ...]
    required_documents: tuple[str, ...]
    application_portal: str


SCHEME_RULES: tuple[SchemeRule, ...] = (

    SchemeRule(
        scheme_name="NSP Central Sector Scholarship (CSSS)",
        category="education",
        keywords=("nsp", "central sector", "csss", "scholarship", "college", "university", "meritorious"),
        required_profile_fields=("education_level", "income_annual", "has_aadhaar"),
        required_documents=("Income certificate", "Aadhaar"),
        application_portal="https://scholarships.gov.in/",
    ),
    SchemeRule(
        scheme_name="Maharashtra EBC Scholarship",
        category="education",
        keywords=("maharashtra", "ebc", "scholarship", "economically backward", "tuition", "exam fee", "cap"),
        required_profile_fields=("income_annual", "state", "has_aadhaar"),
        required_documents=("Income certificate", "Domicile certificate", "Aadhaar"),
        application_portal="https://mahadbt.maharashtra.gov.in/",
    ),
    SchemeRule(
        scheme_name="PM Kaushal Vikas Yojana (PMKVY)",
        category="skill_development",
        keywords=("pmkvy", "kaushal vikas", "skill", "training", "unemployed", "youth"),
        required_profile_fields=("has_aadhaar", "has_pan"),
        required_documents=("Aadhaar", "PAN Card"),
        application_portal="https://www.pmkvyofficial.org/",
    ),
    SchemeRule(
        scheme_name="Vidya Lakshmi Portal",
        category="education_loan",
        keywords=("vidya lakshmi", "education loan", "bank", "celaf"),
        required_profile_fields=("has_aadhaar", "has_pan", "has_passport"),
        required_documents=("Aadhaar", "PAN Card", "Passport"),
        application_portal="https://www.vidyalakshmi.co.in/",
    ),
    SchemeRule(
        scheme_name="PM Mudra Yojana (PMMY)",
        category="business_loan",
        keywords=("mudra", "pmmy", "business loan", "collateral free", "shishu", "kishor", "tarun", "micro", "small enterprise"),
        required_profile_fields=("has_aadhaar", "has_pan", "income_annual"),
        required_documents=("Aadhaar", "PAN Card", "Income certificate"),
        application_portal="https://www.mudra.org.in/",
    ),
)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _extract_income(text: str) -> int | None:
    patterns = (
        r"(?:income|earning|earn|salary)[^\d]{0,20}(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|l|k|thousand)?",
        r"(\d+(?:\.\d+)?)\s*(lakh|lakhs|lac|l|k|thousand)\s*(?:annual|yearly|per year|income)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        amount = float(match.group(1))
        unit = match.group(2)
        if unit in {"lakh", "lakhs", "lac", "l"}:
            return int(amount * 100000)
        if unit in {"k", "thousand"}:
            return int(amount * 1000)
        return int(amount)
    return None


def _extract_land(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(acre|acres|hectare|hectares)", text)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2)
    if unit.startswith("hectare"):
        return round(value * 2.47105, 2)
    return value


def _field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def _friendly_fields(fields: list[str]) -> list[str]:
    return [_field_label(field) for field in fields]


def _uncertainty_question(field: str) -> str:
    questions = {
        "has_aadhaar": "Do you have an Aadhaar-linked bank account?",
        "has_bank_account": "Do you have an active bank account?",
        "land_ownership_acres": "Do you own cultivable land?",
        "income_annual": "What is your annual household or parental income?",
        "has_vending_certificate": "Do you have a vending certificate or ULB/TVC recommendation?",
        "state": "Which state are you from?",
    }
    return questions.get(field, f"Can you confirm the applicant's {_field_label(field).lower()}?")


def _question_for_field(field: str) -> str:
    questions = {
        "income_annual": "What is your annual household or parental income?",
        "land_ownership_acres": "Do you own cultivable land?",
        "category": "What is your applicant category (SC, ST, OBC, or General)?",
        "urban_rural": "Are you living in an urban or rural area?",
        "education_level": "Which class or course are you currently enrolled in?",
        "occupation": "What is your current occupation?",
        "has_aadhaar": "Do you have an Aadhaar-linked bank account?",
        "has_bank_account": "Do you have an active bank account?",
        "has_vending_certificate": "Do you have a vending certificate or ULB/TVC recommendation?",
        "has_ulb_recommendation": "Do you have a letter of recommendation from your ULB/TVC?",
        "has_pucca_house": "Do you already own a pucca house?",
        "state": "Which state are you from?",
    }
    return questions.get(field, f"Can you confirm the applicant's {_field_label(field).lower()}?")


def _uncertainty_detail(field: str, phrase: str | None = None) -> dict[str, Any]:
    return {
        "field": field,
        "label": _field_label(field),
        "stated_uncertainty": phrase or "The user explicitly said they are unsure.",
        "why_required": FIELD_WHY_REQUIRED.get(field, f"{_field_label(field)} is required to complete the eligibility check."),
        "verification_steps": FIELD_VERIFY_STEPS.get(
            field,
            [f"Ask the applicant to provide a valid document or confirmation for {_field_label(field).lower()}."],
        ),
        "question": _uncertainty_question(field),
    }


def _detect_uncertainty(text: str, field: str, term_patterns: tuple[str, ...]) -> dict[str, Any] | None:
    joined = "|".join(term_patterns)
    uncertainty_phrases = (
        r"not sure|do not know|dont know|don't know|unknown|unsure|maybe|unaware|i am unaware|"
        r"i haven't checked|i havent checked|haven't checked|havent checked"
    )
    patterns = (
        rf"\b({uncertainty_phrases})\b[^.]*({joined})",
        rf"({joined})[^.]*\b({uncertainty_phrases})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _uncertainty_detail(field, match.group(0))
    return None


def _extract_optional_bool(text: str, field: str, term_patterns: tuple[str, ...]) -> bool | None:
    joined = "|".join(term_patterns)
    if _detect_uncertainty(text, field, term_patterns):
        return None
    if re.search(rf"\b(no|not|without|do not have|dont have|don't have)\b[^.]*({joined})", text):
        return False
    if re.search(rf"\b(has|have|with|available|seeded)\b[^.]*({joined})", text):
        return True
    if re.search(rf"({joined})", text):
        return True
    return None


def classify_intent(query: str) -> str:
    text = query.lower().strip()

    # 1. Fast regex checks for invalid intents
    out_of_scope_patterns = [
        # Programming & Software
        r"\b(react|redux|python|c\+\+|java|javascript|html|css|sql|git|npm|api|coding|programming|software|developer|framework|repo|github|compile|debug)\b",
        # Finance & Stock Market
        r"\b(stock price|stock market|nvidia|nasdaq|crypto|bitcoin|shares|investing|portfolio|market cap)\b",
        # Sports
        r"\b(ipl|cricket|football|soccer|score|match|game|player|won yesterday|championship|tournament)\b",
        # Entertainment
        r"\b(movie|song|music|actor|actress|netflix|celebrity|oscar|hollywood|bollywood)\b",
    ]

    for pattern in out_of_scope_patterns:
        if re.search(pattern, text):
            return "OUT_OF_SCOPE"

    # 2. Fast regex checks for valid intents
    in_scope_patterns = [
        r"\b(eligible|eligibility|scheme|subsidy|benefit|welfare|pension|kisan|kusum|svanidhi|awas|pmmis|scholarship|entitlement|document|citizen|government|portal|apply|qualify)\b",
        r"\bpm-kisan\b",
        r"\bpmsvanidhi\b",
        r"\bpm-kusum\b",
        r"\bpmay-u\b"
    ]

    for pattern in in_scope_patterns:
        if re.search(pattern, text):
            return "Continue"

    # 3. LLM classification fallback
    try:
        from app.services.query_service import USE_OLLAMA, get_llm
        from app.services.ollama_service import get_ollama_llm
        if USE_OLLAMA:
            llm = get_ollama_llm()
        else:
            llm = get_llm()
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a precise intent classifier. Classify the user query as 'Continue' (if it is related to government schemes, eligibility, benefits, welfare, required documents, citizen services) "
                    "or 'OUT_OF_SCOPE' (if it is about programming, software, finance, stock price, sports, entertainment, general knowledge). Respond with EXACTLY one word: 'Continue' or 'OUT_OF_SCOPE'."
                )
            },
            {"role": "user", "content": f"Query: \"{query}\"\nClassification:"}
        ]
        response = llm.create_chat_completion(messages, temperature=0.0, max_tokens=5)
        content = response["choices"][0]["message"]["content"].strip().upper()
        if "CONTINUE" in content:
            return "Continue"
        elif "OUT_OF_SCOPE" in content:
            return "OUT_OF_SCOPE"
    except Exception as e:
        logger.warning("Failed to classify intent using LLM: %s. Falling back to default.", e)

    return "OUT_OF_SCOPE"


def extract_profile(raw_query: str) -> dict[str, Any]:
    text = raw_query.lower()

    occupation = None
    if _contains_any(text, ("street vendor", "vendor", "hawker", "vending")):
        occupation = "street_vendor"
    elif _contains_any(text, ("farmer", "kisan", "cultivator", "agriculture")):
        occupation = "farmer"
    elif _contains_any(text, ("student", "college", "class 11", "class 12", "post matric", "scholarship")):
        occupation = "student"

    category = None
    for candidate in ("sc", "st", "obc", "general"):
        if re.search(rf"\b{candidate}\b", text):
            category = candidate.upper() if candidate != "general" else "General"
            break

    education_level = None
    if _contains_any(text, ("post matric", "class 11", "class 12", "college", "degree", "diploma")):
        education_level = "post_matric"
    elif "student" in text:
        education_level = "student"

    urban_rural = None
    if _contains_any(text, ("urban", "city", "municipal", "slum", "ulb")):
        urban_rural = "urban"
    elif _contains_any(text, ("rural", "village", "gram", "panchayat")):
        urban_rural = "rural"

    uncertainties = []
    for field, patterns in (
        ("has_aadhaar", ("aadhaar",)),
        ("has_bank_account", ("bank account", "bank")),
        ("has_vending_certificate", ("vending certificate", "certificate of vending")),
        ("has_ulb_recommendation", ("ulb recommendation", "tvc recommendation", "letter from ulb")),
        ("has_pan", ("pan card", "pan")),
        ("has_passport", ("passport",)),
    ):
        detail = _detect_uncertainty(text, field, patterns)
        if detail:
            uncertainties.append(detail)

    return {
        "occupation": occupation,
        "income_annual": _extract_income(text),
        "land_ownership_acres": _extract_land(text),
        "category": category,
        "state": None,
        "urban_rural": urban_rural,
        "education_level": education_level,
        "age": None,
        "existing_benefits": [],
        "has_aadhaar": _extract_optional_bool(text, "has_aadhaar", ("aadhaar",)),
        "has_bank_account": _extract_optional_bool(text, "has_bank_account", ("bank account", "bank")),
        "has_vending_certificate": _extract_optional_bool(text, "has_vending_certificate", ("vending certificate", "certificate of vending")),
        "has_ulb_recommendation": _extract_optional_bool(text, "has_ulb_recommendation", ("ulb recommendation", "tvc recommendation", "letter from ulb")),
        "has_pucca_house": _extract_optional_bool(text, "has_pucca_house", ("pucca house", "pukka house")) if _extract_optional_bool(text, "has_pucca_house", ("pucca house", "pukka house")) is not None else (False if _contains_any(text, ("no pucca", "without pucca", "does not own pucca", "kutcha")) else None),
        "is_govt_employee": True if _contains_any(text, ("government employee", "govt employee")) else None,
        "pays_income_tax": True if _contains_any(text, ("income tax payer", "pays income tax", "pay income tax")) else None,
        "owns_motorized_vehicle": True if _contains_any(text, ("motorized vehicle", "motorised vehicle", "four wheeler")) else None,
        "is_institutional_landholder": True if "institutional landholder" in text else None,
        "has_pan": _extract_optional_bool(text, "has_pan", ("pan card", "pan")),
        "has_passport": _extract_optional_bool(text, "has_passport", ("passport",)),
        "uncertainties": uncertainties,
    }


def _profile_terms(profile: dict[str, Any]) -> str:
    parts = []
    for key in ("occupation", "category", "urban_rural", "education_level"):
        if profile.get(key):
            parts.append(str(profile[key]).replace("_", " "))
    if profile.get("income_annual"):
        parts.append(f"income {profile['income_annual']}")
    if profile.get("land_ownership_acres"):
        parts.append(f"land {profile['land_ownership_acres']} acres")
    return " ".join(parts)


def _candidate_rules(raw_query: str, profile: dict[str, Any]) -> list[SchemeRule]:
    text = f"{raw_query.lower()} {_profile_terms(profile).lower()}"
    scored = []
    for rule in SCHEME_RULES:
        score = sum(1 for keyword in rule.keywords if _keyword_matches(text, keyword))
        if rule.scheme_name.lower() in text:
            score += 3
        if score:
            scored.append((score, rule))

    if not scored and profile.get("occupation") == "farmer":
        return [rule for rule in SCHEME_RULES if rule.scheme_name in {"PM-KISAN", "PM-KUSUM"}]

    scored.sort(key=lambda item: item[0], reverse=True)
    top_score = scored[0][0] if scored else 0
    return [rule for score, rule in scored[:4] if score >= 1 or score == top_score]


def _keyword_matches(text: str, keyword: str) -> bool:
    if len(keyword) <= 3 and keyword.isalnum():
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None
    return keyword in text


def _missing_fields(profile: dict[str, Any], rule: SchemeRule) -> list[str]:
    return [field for field in rule.required_profile_fields if profile.get(field) is None]


def _verdict(profile: dict[str, Any], rule: SchemeRule, missing: list[str]) -> str:
    if missing:
        return "PENDING_DOCS"

    income = profile.get("income_annual")
    if rule.scheme_name == "Post-Matric Scholarship":
        if income is not None and income > 250000:
            return "INELIGIBLE"
        if profile.get("category") not in {"SC", "ST", "OBC"}:
            return "PENDING_DOCS"

    if rule.scheme_name == "PMAY-U" and profile.get("has_pucca_house") is True:
        return "INELIGIBLE"

    if rule.scheme_name == "PM-KISAN" and not profile.get("land_ownership_acres"):
        return "PENDING_DOCS"

    return "LIKELY_ELIGIBLE"


def _profile_completeness(profile: dict[str, Any]) -> int:
    fields = [
        "occupation", "income_annual", "land_ownership_acres", "category",
        "state", "urban_rural", "education_level", "age", "existing_benefits",
        "has_aadhaar", "has_bank_account", "has_vending_certificate",
        "has_ulb_recommendation", "has_pucca_house", "is_govt_employee",
        "pays_income_tax", "owns_motorized_vehicle", "is_institutional_landholder"
    ]
    filled = sum(1 for f in fields if profile.get(f) is not None)
    return round((filled / len(fields)) * 100)


def _citation_quality(text: str) -> int:
    text_lower = text.lower()
    pos_terms = ["eligibility", "criteria", "beneficiary", "required documents", "exclusion"]
    neg_terms = ["implementation", "administration", "monitoring", "pmu", "tender"]
    
    pos_count = sum(1 for term in pos_terms if term in text_lower)
    neg_count = sum(1 for term in neg_terms if term in text_lower)
    
    score = 5 + (pos_count * 1.5) - (neg_count * 1.5)
    return max(0, min(10, round(score)))


def _generate_scorecard(
    met_criteria: list[str],
    missing_information: list[str],
    failed_conditions: list[str],
) -> list[str]:
    scorecard = []
    for met in met_criteria:
        scorecard.append(f"✓ {met}")
    for missing in missing_information:
        scorecard.append(f"? {missing}")
    for failed in failed_conditions:
        scorecard.append(f"✗ {failed}")
    return scorecard


def _eligibility_confidence(
    status: str,
    profile_completeness_pct: float,
    citations: list[dict[str, Any]],
    missing_docs: list[Any],
    required_docs: list[Any]
) -> int:
    if status == "NOT_ELIGIBLE":
        return 0
        
    # Rule Match Score
    rule_match_score = 100 if status == "ELIGIBLE" else 50
    
    # Retrieval Quality Score
    if citations:
        avg_citation_quality = sum(c.get("citation_quality_score", 5) for c in citations) / len(citations)
    else:
        avg_citation_quality = 5.0
    retrieval_quality = avg_citation_quality * 10
    
    # Document Verification Score
    if required_docs:
        doc_verification = max(0, 100 - (len(missing_docs) / len(required_docs) * 100))
    else:
        doc_verification = 100
        
    # Weighted average
    score = (
        0.4 * rule_match_score +
        0.2 * profile_completeness_pct +
        0.2 * retrieval_quality +
        0.2 * doc_verification
    )
    return max(0, min(100, round(score)))


def _generate_llm_explanation(
    status: str,
    confidence: int,
    reasoning: str,
    scorecard: list[str],
    missing_information: list[str],
    required_documents: list[str],
    next_steps: list[str],
    policy_citations: list[dict[str, Any]],
) -> str | None:
    try:
        from app.services.query_service import USE_OLLAMA, get_llm
        from app.services.ollama_service import get_ollama_llm
        if USE_OLLAMA:
            llm = get_ollama_llm()
        else:
            llm = get_llm()
        scorecard_str = "\n".join(scorecard)
        missing_str = ", ".join(missing_information) if missing_information else "None"
        docs_str = ", ".join(required_documents) if required_documents else "None"
        steps_str = "\n".join(f"- {s}" for s in next_steps) if next_steps else "- None"
        citations_str = "\n".join(
            f"- {c['file_name']} (Page {c.get('page_range')}): \"{c.get('excerpt', '')[:100]}...\""
            for c in policy_citations
        ) if policy_citations else "None"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an explainable entitlement advisor. Generate a citizen-friendly explanation summary. "
                    "You must output exactly the layout specified below, and do not use any internal field names."
                )
            },
            {
                "role": "user",
                "content": f"""
Based on the following data, write a citizen-friendly explanation summary.

Status: {status}
Confidence: {confidence}%
Reasoning: {reasoning}
Eligibility Scorecard:
{scorecard_str}
Missing Information: {missing_str}
Required Documents: {docs_str}
Next Steps:
{steps_str}
Policy Citations:
{citations_str}

Format the response exactly like this (use these exact headers):

Status: {status}
Confidence: {confidence}%
Reason: <brief conversational summary of the decision>
Matched Conditions:
<bullet points of matched conditions, e.g. - Farmer>
Failed Conditions:
<bullet points of failed conditions or - None>
Missing Information:
<bullet points of missing fields or - None>
Required Documents:
<bullet points of required docs or - None>
Next Steps:
<bullet points of next steps or - None>
"""
            }
        ]
        response = llm.create_chat_completion(messages, temperature=0.1, max_tokens=1000)
        content = response["choices"][0]["message"]["content"]
        if content and "Error:" not in content:
            return content.strip()
    except Exception as e:
        print("LLM EXCEPTION:", str(e))
        logger.warning("Failed to generate LLM explanation: %s. Falling back to python explanation.", e)
    return None


def _citation(result: dict[str, Any]) -> dict[str, Any]:
    excerpt = (result.get("text") or "")[:500]
    quality = _citation_quality(excerpt)
    return {
        "chunk_id": result.get("chunk_id"),
        "file_name": result.get("file_name"),
        "page_range": result.get("page_range"),
        "section_path": result.get("section_path"),
        "score": float(result.get("score") or 0),
        "eligibility_signal": bool(result.get("eligibility_signal")),
        "low_value_signal": bool(result.get("low_value_signal")),
        "excerpt": excerpt,
        "citation_quality_score": quality,
    }


def _document_for_field(field: str) -> str | None:
    return FIELD_DOCUMENTS.get(field)


def _missing_documents_for_fields(fields: list[str], rule: SchemeRule) -> list[dict[str, str]]:
    docs = []
    seen = set()

    for field in fields:
        doc = _document_for_field(field)
        if doc and doc not in seen:
            docs.append({"document": doc, "reason": f"Needed to verify {_field_label(field)}"})
            seen.add(doc)

    for doc in rule.required_documents:
        if doc not in seen:
            docs.append({"document": doc, "reason": f"Normally required for {rule.scheme_name}"})
            seen.add(doc)

    return docs


def _decision_from_reasoning(reasoning: dict[str, Any]) -> str:
    if reasoning["failed_conditions"]:
        return "NOT_ELIGIBLE"
    if reasoning["missing_information"]:
        return "PENDING_DOCS"
    return "ELIGIBLE"


def _build_reasoning_object(
    rule: SchemeRule,
    graph_match: dict[str, Any],
    missing: list[str],
) -> dict[str, Any]:
    failed_conditions = list(graph_match.get("unmet_criteria") or [])
    failed_conditions.extend(graph_match.get("disqualifiers") or [])

    reasoning = {
        "matched_conditions": graph_match.get("met_criteria") or [],
        "failed_conditions": failed_conditions,
        "missing_information": _friendly_fields(missing),
        "required_documents": list(rule.required_documents),
        "decision": "",
    }
    reasoning["decision"] = _decision_from_reasoning(reasoning)
    return reasoning


def _decision_status(graph_match: dict[str, Any], missing: list[str]) -> str:
    if graph_match.get("disqualifiers") or graph_match.get("unmet_criteria"):
        return "NOT_ELIGIBLE"

    met_count = len(graph_match.get("met_criteria") or [])
    if missing and met_count == 0:
        return "PENDING_DOCS"
    if missing:
        return "PENDING_DOCS"
    return "ELIGIBLE"


def _machine_verdict(status: str) -> str:
    return {
        "ELIGIBLE": "LIKELY_ELIGIBLE",
        "NOT_ELIGIBLE": "INELIGIBLE",
        "PENDING_DOCS": "PENDING_DOCS",
        "INSUFFICIENT_INFORMATION": "INSUFFICIENT_INFORMATION",
    }[status]


def _rule_reasons(status: str, graph_match: dict[str, Any], missing: list[str]) -> list[str]:
    reasons = []
    if graph_match.get("met_criteria"):
        reasons.append("The citizen profile satisfies the matched eligibility conditions.")
    if graph_match.get("unmet_criteria"):
        reasons.extend(f"Unmet condition: {item}" for item in graph_match["unmet_criteria"])
    if graph_match.get("disqualifiers"):
        reasons.extend(f"Disqualifier detected: {item}" for item in graph_match["disqualifiers"])
    if missing:
        reasons.append(f"Mandatory details are still needed: {', '.join(_friendly_fields(missing))}.")
    if not reasons:
        reasons.append("No explicit disqualifier was found in the available profile information.")
    return reasons


def _evaluate_rule(
    rule: SchemeRule,
    profile: dict[str, Any],
    graph_match: dict[str, Any],
    verified_docs: list[str] = None
) -> dict[str, Any]:
    missing = graph_match.get("missing_profile_fields") or _missing_fields(profile, rule)
    reasoning = _build_reasoning_object(rule, graph_match, missing)
    status = reasoning["decision"]
    missing_documents = _missing_documents_for_fields(missing, rule)

    if verified_docs is None:
        verified_docs = []

    # FILTER missing_documents based on verified_docs
    filtered_missing_documents = []
    for doc in missing_documents:
        if doc['document'] not in verified_docs:
            filtered_missing_documents.append(doc)
            
    if status == "PENDING_DOCS" and not missing and not filtered_missing_documents:
        status = "ELIGIBLE"
        reasoning["decision"] = "ELIGIBLE"

    if status == "NOT_ELIGIBLE":
        filtered_missing_documents = []

    return {
        "scheme_name": rule.scheme_name,
        "status": status,
        "verdict": _machine_verdict(status),
        "reasoning": reasoning,
        "reasons": _rule_reasons(status, graph_match, missing),
        "matched_conditions": reasoning["matched_conditions"],
        "failed_conditions": reasoning["failed_conditions"],
        "unmatched_conditions": graph_match.get("unmet_criteria") or [],
        "missing_fields": missing,
        "missing_information": reasoning["missing_information"],
        "missing_documents": filtered_missing_documents,
        "disqualifiers": graph_match.get("disqualifiers") or [],
    }


def _generic_scheme_explanation(
    scheme_name: str,
    verdict: str,
    matched_conditions: list[str],
    failed_conditions: list[str],
    missing_information: list[str],
    missing_documents: list[str],
    next_steps: list[str],
) -> str:
    verdict_friendly = verdict.replace("_", " ").title()
    parts = [f"Based on our evaluation of {scheme_name}, the status is {verdict_friendly}."]
    
    if matched_conditions:
        matched_str = ", ".join(matched_conditions)
        parts.append(f"You satisfy the conditions for: {matched_str}.")
        
    if failed_conditions:
        failed_str = ", ".join(failed_conditions)
        parts.append(f"However, you do not meet the criteria for: {failed_str}.")
        
    if verdict not in ("INELIGIBLE", "NOT_ELIGIBLE"):
        if missing_information or missing_documents:
            verif_parts = []
            if missing_information:
                verif_parts.append(", ".join(missing_information))
            if missing_documents:
                verif_parts.append(f"supporting documents for {', '.join(missing_documents)}")
            parts.append(f"Before eligibility can be confirmed, the system must verify {', and '.join(verif_parts)}.")
            
        if next_steps:
            steps_str = ", ".join(next_steps)
            parts.append(f"Next steps: {steps_str}.")
        
    return " ".join(parts)


def _generate_scheme_llm_explanation(
    scheme_name: str,
    verdict: str,
    matched_conditions: list[str],
    failed_conditions: list[str],
    missing_information: list[str],
    missing_documents: list[str],
    next_steps: list[str],
    fallback_reasoning: str,
) -> str:
    try:
        from app.services.query_service import USE_OLLAMA, get_llm
        from app.services.ollama_service import get_ollama_llm
        if USE_OLLAMA:
            llm = get_ollama_llm()
        else:
            llm = get_llm()
        
        matched_str = ", ".join(matched_conditions) if matched_conditions else "None"
        failed_str = ", ".join(failed_conditions) if failed_conditions else "None"
        missing_info_str = ", ".join(missing_information) if missing_information else "None"
        missing_docs_str = ", ".join(missing_documents) if missing_documents else "None"
        steps_str = ", ".join(next_steps) if next_steps else "None"
        
        system_prompt = (
            "You are a helpful government entitlement assistant. Explain the citizen's eligibility for the specified scheme. "
            "You must output exactly a single paragraph of explanation. Use simple, citizen-friendly language. "
            "IMPORTANT: Do not make decisions about eligibility yourself. Do not change the verdict. Do not use any internal database field names. "
            "Focus only on explaining the existing verdict using the provided details."
        )
        
        user_prompt = (
            f"Scheme: {scheme_name}\n"
            f"Verdict: {verdict}\n"
            f"Matched Conditions: {matched_str}\n"
            f"Failed Conditions: {failed_str}\n"
            f"Needs Verification: {missing_info_str}\n"
            f"Missing Documents: {missing_docs_str}\n"
            f"Next Steps: {steps_str}\n\n"
            "Generate a citizen-friendly explanation of why they got this verdict and what they should do next. "
            "Keep it short, clear, and professional. Output only the paragraph text."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = llm.create_chat_completion(messages, temperature=0.0, max_tokens=150)
        content = response["choices"][0]["message"]["content"]
        if content and "Error:" not in content and not content.startswith("Error:"):
            return content.strip()
    except Exception as e:
        logger.warning("Failed to generate scheme LLM explanation: %s. Falling back.", e)
    return fallback_reasoning


def _format_scheme_explanation(
    rule: SchemeRule,
    evaluation: dict[str, Any],
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    status = evaluation["status"].replace("_", " ").title()
    name = rule.scheme_name

    # Build next steps
    next_steps = []
    for field in evaluation.get("missing_fields", []):
        next_steps.append(f"Verify {_field_label(field)}")
    for doc_item in evaluation.get("missing_documents", []):
        doc_name = doc_item.get("document")
        next_steps.append(f"Submit document '{doc_name}'")

    reasoning = _generic_scheme_explanation(
        scheme_name=name,
        verdict=evaluation["verdict"],
        matched_conditions=evaluation["matched_conditions"],
        failed_conditions=evaluation["failed_conditions"],
        missing_information=evaluation["missing_information"],
        missing_documents=[d.get("document") for d in evaluation.get("missing_documents", [])],
        next_steps=next_steps
    )

    return {
        "eligibility_status": status,
        "reasoning": reasoning,
        "matched_conditions": evaluation["matched_conditions"],
        "missing_information": evaluation["missing_information"],
        "required_documents": list(rule.required_documents),
        "next_steps": next_steps,
        "policy_citations": [
            {
                "file_name": citation.get("file_name"),
                "page_range": citation.get("page_range"),
                "excerpt": citation.get("excerpt"),
            }
            for citation in citations
        ],
    }



def _overall_status(evaluations: list[dict[str, Any]]) -> str:
    if evaluations:
        primary = evaluations[0]["status"]
        if primary in {"ELIGIBLE", "PENDING_DOCS"}:
            return primary

    statuses = [item["status"] for item in evaluations]
    if "ELIGIBLE" in statuses:
        return "ELIGIBLE"
    if "PENDING_DOCS" in statuses:
        return "PENDING_DOCS"
    return "NOT_ELIGIBLE"


def _overall_verdict(status: str) -> str:
    return _machine_verdict(status)


def _debug_log(event: str, payload: dict[str, Any]) -> None:
    logger.info("entitlement_%s %s", event, json.dumps(payload, default=str))


def _scheme_readiness(profile: dict[str, Any], rule: SchemeRule) -> int:
    total = len(rule.required_profile_fields)
    if total == 0:
        return 100
    present = sum(1 for field in rule.required_profile_fields if profile.get(field) is not None)
    return round((present / total) * 100)


def _application_readiness(verdict: str, missing_fields: list[str], missing_docs: list[Any]) -> str:
    if verdict == "ELIGIBLE":
        return "READY"
    if verdict in ("INELIGIBLE", "NOT_ELIGIBLE"):
        return "NOT_ELIGIBLE"
    if verdict == "LIKELY_ELIGIBLE":
        return "NEEDS_VERIFICATION"
    
    # It's PENDING_DOCS or other statuses
    if missing_fields:
        return "NEEDS_VERIFICATION"
    if missing_docs:
        return "MISSING_DOCUMENTS"
    return "NEEDS_VERIFICATION"


def _readiness_sublabel(verdict: str, missing_fields: list[str], missing_docs: list[Any]) -> str:
    if verdict in ("INELIGIBLE", "NOT_ELIGIBLE"):
        return "Unmet criteria"
    if missing_fields:
        first_field = missing_fields[0]
        friendly = FIELD_LABELS.get(first_field, first_field.replace("_", " ").title())
        return f"Ready after {friendly} verification"
    if missing_docs:
        doc_count = len(missing_docs)
        doc_word = "document" if doc_count == 1 else "documents"
        return f"{doc_count} {doc_word} pending"
    if verdict == "ELIGIBLE":
        return "Ready to Apply"
    if verdict == "LIKELY_ELIGIBLE":
        return "Verification Required"
    return "Verification pending"


def build_determination(conn: Any, raw_query: str, profile: dict[str, Any], trigger_llm: bool = True, verified_docs: list[str] = None) -> tuple[list[dict], dict]:
    rules = _candidate_rules(raw_query, profile)
    if not rules:
        rules = list(SCHEME_RULES[:])
    _debug_log("profile_extracted", {"profile": profile, "candidate_rules": [rule.scheme_name for rule in rules]})

    graph_matches = {
        item["scheme_name"]: item
        for item in match_entitlement_graph(profile, [rule.scheme_name for rule in rules])
    }

    scheme_matches = []
    determinations = []
    evaluations = []

    for rule in rules:
        retrieval_query = " ".join([raw_query, rule.scheme_name, _profile_terms(profile)])
        retrieved = retrieve_entitlement_clauses(
            conn,
            retrieval_query,
            scheme_name=rule.scheme_name,
            language=None,
            top_k=3,
        )
        graph_match = graph_matches.get(rule.scheme_name, {})
        evaluation = _evaluate_rule(rule, profile, graph_match, verified_docs)
        verdict = evaluation["verdict"]
        citations = [_citation(item) for item in retrieved]
        evaluations.append(evaluation)

        _debug_log(
            "retrieval",
            {
                "scheme_name": rule.scheme_name,
                "retrieved_chunks": [
                    {
                        "chunk_id": item.get("chunk_id"),
                        "file_name": item.get("file_name"),
                        "heading": item.get("chunk_heading"),
                        "score": float(item.get("score") or 0),
                        "eligibility_signal": bool(item.get("eligibility_signal")),
                        "low_value_signal": bool(item.get("low_value_signal")),
                    }
                    for item in retrieved
                ],
            },
        )
        _debug_log("rule_evaluation", evaluation)

        scheme_matches.append(
            {
                "scheme_name": rule.scheme_name,
                "scheme_category": rule.category,
                "retrieved_chunks": [item.get("chunk_id") for item in retrieved],
                "score": float(retrieved[0].get("score") or 0) if retrieved else 0.0,
                "eligibility_citation_count": sum(1 for item in retrieved if item.get("eligibility_signal")),
            }
        )

        readiness_score = _scheme_readiness(profile, rule)
        app_readiness = _application_readiness(verdict, evaluation["missing_fields"], evaluation["missing_documents"])
        readiness_sub = _readiness_sublabel(verdict, evaluation["missing_fields"], evaluation["missing_documents"])
        explanation_obj = _format_scheme_explanation(rule, evaluation, citations)

        determinations.append(
            {
                "scheme_name": rule.scheme_name,
                "verdict": verdict,
                "decision_status": evaluation["status"],
                "reasoning": evaluation["reasoning"],
                "reasons": evaluation["reasons"],
                "benefit": graph_match.get("benefit"),
                "met_criteria": evaluation["matched_conditions"],
                "unmet_criteria": evaluation["unmatched_conditions"],
                "failed_conditions": evaluation["failed_conditions"],
                "disqualifiers": evaluation["disqualifiers"],
                "missing_profile_fields": evaluation["missing_fields"],
                "missing_information": evaluation["missing_information"],
                "missing_documents": evaluation["missing_documents"],
                "required_documents": list(rule.required_documents),
                "application_portal": rule.application_portal,
                "citations": citations,
                "explanation": explanation_obj,
                "next_steps": explanation_obj["next_steps"],
                "readiness_score": readiness_score,
                "application_readiness": app_readiness,
                "readiness_sublabel": readiness_sub,
            }
        )

    overall_status = _overall_status(evaluations)
    overall = _overall_verdict(overall_status)

    edge_cases = check_edge_cases(raw_query, profile, scheme_matches, determinations)
    if verified_docs:
        edge_cases["missing_documents"] = [d for d in edge_cases.get("missing_documents", []) if d["document"] not in verified_docs]
    missing_documents = edge_cases["missing_documents"]
    uncertainty_followups = profile.get("uncertainties", [])
    uncertainty_fields = {item["field"] for item in uncertainty_followups}
    generic_questions = [
        question
        for question in edge_cases["clarification_questions"]
        if question not in {_question_for_field(field) for field in uncertainty_fields}
    ]
    clarification_questions = _unique_items([item["question"] for item in uncertainty_followups] + generic_questions)
    missing_information = _friendly_fields(edge_cases["missing_profile_fields"])

    # Step 9: Benefit Optimization
    qualifying_schemes = [d for d in determinations if d["verdict"] in ("LIKELY_ELIGIBLE", "PENDING_DOCS")]
    optimized_plan = optimize_benefits(qualifying_schemes)

    # Trigger Ollama explanations only for top 3 optimized schemes
    if trigger_llm:
        top_3_names = {item["scheme_name"] for item in optimized_plan[:3]}
        for det in determinations:
            if det["scheme_name"] in top_3_names:
                missing_docs_list = [d.get("document") for d in det.get("missing_documents", [])] if isinstance(det.get("missing_documents"), list) else []
                llm_reasoning = _generate_scheme_llm_explanation(
                    scheme_name=det["scheme_name"],
                    verdict=det["verdict"],
                    matched_conditions=det["met_criteria"],
                    failed_conditions=det["failed_conditions"],
                    missing_information=det["missing_information"],
                    missing_documents=missing_docs_list,
                    next_steps=det["next_steps"],
                    fallback_reasoning=det["explanation"]["reasoning"]
                )
                det["explanation"]["reasoning"] = llm_reasoning

    # Calculate citizen dynamic verdict summary
    recommended_count = len(qualifying_schemes)
    ready_count = len([d for d in determinations if d.get("application_readiness") == "READY"])
    needs_verif_count = len([d for d in determinations if d.get("application_readiness") == "NEEDS_VERIFICATION"])
    missing_docs_count = len([d for d in determinations if d.get("application_readiness") == "MISSING_DOCUMENTS"])
    
    if recommended_count == 0:
        citizen_summary = "No schemes recommended based on your current profile."
    else:
        parts = []
        parts.append(f"{recommended_count} {'scheme' if recommended_count == 1 else 'schemes'} recommended")
        parts.append(f"{ready_count} fully ready")
        
        req_verif = needs_verif_count + missing_docs_count
        if req_verif > 0:
            parts.append(f"{req_verif} require verification")
        
        citizen_summary = ", ".join(parts)

    explanation_data = _format_overall_explanation(overall_status, determinations, edge_cases, profile)

    determination = {
        "verdict": overall,
        "citizen_verdict": citizen_summary,
        "decision_status": overall_status,
        "application_readiness": explanation_data.get("application_readiness", "NEEDS_VERIFICATION"),
        "readiness_sublabel": explanation_data.get("readiness_sublabel", ""),
        "schemes": determinations,
        "rule_evaluation": evaluations,
        "explanation": explanation_data,
        "edge_cases": edge_cases,
        "missing_documents": missing_documents,
        "uncertainty_followups": uncertainty_followups,
        "adjacent_suggestions": edge_cases["adjacent_suggestions"],
        "clarification_questions": clarification_questions,
        "optimized_benefit_plan": optimized_plan,
        "debug": {
            "missing_fields": edge_cases["missing_profile_fields"],
            "missing_information": missing_information,
            "retrieved_chunks": scheme_matches,
            "rule_evaluation_count": len(evaluations),
        },
        "notes": [
            "This is a deterministic first-pass entitlement screening based on ingested scheme documents.",
            "Final eligibility should be verified by an officer against official documents and current scheme rules.",
        ],
    }
    _debug_log(
        "final_decision",
        {
            "decision_status": overall_status,
            "verdict": overall,
            "missing_fields": edge_cases["missing_profile_fields"],
            "clarification_questions": clarification_questions,
        },
    )
    
    # Developer diagnostics logging
    explanation_data = determination["explanation"]
    citations_list = determinations[0].get("citations", []) if determinations else []
    avg_retrieval_quality = sum(c.get("citation_quality_score", 5) for c in citations_list) / len(citations_list) if citations_list else 5.0
    
    diagnostics = {
        "profile_completeness": f"{explanation_data['profile_completeness']}%",
        "retrieval_quality_score": f"{avg_retrieval_quality:.1f}/10",
        "confidence_score": f"{explanation_data['confidence']}%",
        "matched_rules": [d["scheme_name"] for d in determinations if d["verdict"] == "LIKELY_ELIGIBLE"],
        "failed_rules": [d["scheme_name"] for d in determinations if d["verdict"] == "INELIGIBLE"],
        "selected_citations": [
            {
                "chunk_id": cit.get("chunk_id"),
                "file_name": cit.get("file_name"),
                "citation_quality_score": cit.get("citation_quality_score")
            }
            for d in determinations
            for cit in d.get("citations", [])
        ]
    }
    logger.info("entitlement_developer_diagnostics %s", json.dumps(diagnostics, default=str))

    return scheme_matches, determination


def _format_overall_explanation(
    overall_status: str,
    determinations: list[dict[str, Any]],
    edge_cases: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    eligibility_status = overall_status.replace("_", " ").title()

    # Calculate citizen dynamic verdict summary
    recommended_count = len([d for d in determinations if d["verdict"] in ("LIKELY_ELIGIBLE", "PENDING_DOCS")])
    ready_count = len([d for d in determinations if d.get("application_readiness") == "READY"])
    needs_verif_count = len([d for d in determinations if d.get("application_readiness") == "NEEDS_VERIFICATION"])
    missing_docs_count = len([d for d in determinations if d.get("application_readiness") == "MISSING_DOCUMENTS"])
    
    if recommended_count == 0:
        citizen_summary = "No schemes recommended based on your current profile."
    else:
        parts = []
        parts.append(f"{recommended_count} {'scheme' if recommended_count == 1 else 'schemes'} recommended")
        parts.append(f"{ready_count} fully ready")
        
        req_verif = needs_verif_count + missing_docs_count
        if req_verif > 0:
            parts.append(f"{req_verif} require verification")
        
        citizen_summary = ", ".join(parts)

    # Profile Completeness Score (0-100)
    profile_completeness_pct = _profile_completeness(profile)

    # Citations and Quality
    primary = determinations[0] if determinations else {}
    citations = primary.get("citations", [])
    avg_retrieval_quality = sum(c.get("citation_quality_score", 5) for c in citations) / len(citations) if citations else 5.0

    # Required and missing docs
    required_documents = _unique_items(
        doc
        for item in determinations
        for doc in item.get("required_documents", [])
    )
    missing_documents = edge_cases.get("missing_documents", [])

    # Eligibility Confidence Score (0-100)
    confidence = _eligibility_confidence(
        overall_status,
        profile_completeness_pct,
        citations,
        missing_documents,
        required_documents,
    )

    # Reasoning / Reason
    scheme = primary.get("scheme_name", "the matching scheme")
    uncertainties = profile.get("uncertainties", [])
    
    if overall_status == "ELIGIBLE":
        reasoning = f"You appear eligible for {scheme} because your profile satisfies the required conditions."
    elif overall_status == "PENDING_DOCS":
        reasoning = f"You appear eligible for {scheme}, but we still need to verify some details or obtain required documents before confirming eligibility."
        if uncertainties:
            unresolved = ", ".join(_field_label(u["field"]) for u in uncertainties)
            reasoning += f" Specifically, you expressed uncertainty about: {unresolved}."
    else:
        reasoning = f"You do not appear eligible for the matched schemes due to unmet criteria or disqualifications."

    # Matched conditions
    matched_conditions = _unique_items(
        condition
        for item in determinations
        for condition in item.get("met_criteria", [])
    )

    # Failed conditions
    failed_conditions = _unique_items(
        condition
        for item in determinations
        for condition in item.get("failed_conditions", [])
    )

    # Missing information
    missing_information = _friendly_fields(edge_cases.get("missing_profile_fields", []))

    # Scorecard
    scorecard = _generate_scorecard(matched_conditions, missing_information, failed_conditions)

    # Next steps (combines uncertainty actions and clarification questions)
    next_steps = []
    
    # 1. Uncertainty guides
    for u in uncertainties:
        field_label = _field_label(u["field"])
        why = u["why_required"]
        steps = " ".join(u["verification_steps"])
        q = u["question"]
        next_steps.append(f"Verify {field_label}: {why} How to check: {steps} Follow-up: {q}")
        
    # 2. General clarification questions (excluding fields handled by uncertainty)
    uncertainty_fields = {u["field"] for u in uncertainties}
    for q in edge_cases.get("clarification_questions", []):
        next_steps.append(q)

    # 3. Missing documents
    for doc_item in missing_documents:
        next_steps.append(f"Submit document '{doc_item['document']}' to verify {doc_item['reason']}")

    # Policy citations
    policy_citations = []
    for item in determinations:
        for citation in item.get("citations", [])[:2]:
            policy_citations.append(citation)
    policy_citations = policy_citations[:6]

    # Fallback to local python formatter
    lines = [
        f"Status: {eligibility_status}",
        f"Confidence: {confidence}%",
        f"Reason:\n{reasoning}",
        "Matched Conditions:"
    ]
    if matched_conditions:
        lines.extend(f"- {c}" for c in matched_conditions)
    else:
        lines.append("- None")

    lines.append("Failed Conditions:")
    if failed_conditions:
        lines.extend(f"- {c}" for c in failed_conditions)
    else:
        lines.append("- None")

    lines.append("Missing Information:")
    if missing_information:
        lines.extend(f"- {c}" for c in missing_information)
    else:
        lines.append("- None")

    lines.append("Required Documents:")
    if required_documents:
        lines.extend(f"- {c}" for c in required_documents)
    else:
        lines.append("- None")

    lines.append("Next Steps:")
    if next_steps:
        lines.extend(f"- {step}" for step in next_steps)
    else:
        lines.append("- None")

    lines.append("Policy Citations:")
    if policy_citations:
        for cit in policy_citations:
            pages = f"Page {cit['page_range']}" if cit.get("page_range") else "Page unknown"
            lines.append(f"- {cit['file_name']} ({pages}) (Citation Quality: {cit.get('citation_quality_score', 5)}/10): \"{cit['excerpt'][:150]}...\"")
    else:
        lines.append("- None")

    formatted_text = "\n".join(lines)

    overall_app_readiness = _application_readiness(overall_status, edge_cases.get("missing_profile_fields", []), missing_documents)
    overall_readiness_sub = _readiness_sublabel(overall_status, edge_cases.get("missing_profile_fields", []), missing_documents)

    return {
        "eligibility_status": eligibility_status,
        "reasoning": reasoning,
        "matched_conditions": matched_conditions,
        "failed_conditions": failed_conditions,
        "missing_information": missing_information,
        "required_documents": required_documents,
        "next_steps": next_steps,
        "policy_citations": policy_citations,
        "scorecard": scorecard,
        "confidence": confidence,
        "profile_completeness": profile_completeness_pct,
        "formatted": formatted_text,
        "citizen_verdict": citizen_summary,
        "application_readiness": overall_app_readiness,
        "readiness_sublabel": overall_readiness_sub,
    }


def _unique_items(items) -> list[str]:
    unique = []
    seen = set()
    for item in items:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def _overall_reasoning(status: str, determinations: list[dict[str, Any]]) -> str:
    primary = determinations[0] if determinations else {}
    scheme = primary.get("scheme_name", "the matching scheme")
    if status == "ELIGIBLE":
        return f"The strongest match is {scheme}; the available profile satisfies its known mandatory conditions."
    if status == "PENDING_DOCS":
        return f"The user appears to match {scheme}, but mandatory documents or profile details must be verified before confirming eligibility."
    return "The available profile triggers unmet eligibility conditions or exclusions for the matched schemes."


def _clarification_questions(determinations: list[dict[str, Any]]) -> list[str]:
    labels = {
        "income_annual": "What is the annual household or parental income?",
        "land_ownership_acres": "How much cultivable land is owned or leased?",
        "category": "What is the applicant category: SC, ST, OBC, or General?",
        "urban_rural": "Is the applicant in an urban or rural area?",
        "education_level": "What class/course is the student currently enrolled in?",
        "occupation": "What is the applicant's occupation?",
        "has_aadhaar": "Is Aadhaar available and seeded where required?",
        "has_bank_account": "Is a bank account available and active?",
        "has_vending_certificate": "Does the vendor have a vending certificate or ULB/TVC recommendation?",
        "has_pucca_house": "Does the household already own a pucca house?",
    }
    questions = []
    seen = set()
    for item in determinations:
        for field in item.get("missing_profile_fields", []):
            question = labels.get(field)
            if question and question not in seen:
                questions.append(question)
                seen.add(question)
    return questions[:5]


def log_all_schemes_audit(citizen_id: str | None, query_id: str | None, determinations: list[dict]):
    if not citizen_id:
        return
    try:
        for d in determinations:
            action = "RECOMMEND" if d["verdict"] == "LIKELY_ELIGIBLE" else ("REJECT" if d["verdict"] == "INELIGIBLE" else "PENDING_VERIFICATION")
            decision_trace = {
                "verdict": d["verdict"],
                "reasons": d["reasons"],
                "met_criteria": d["met_criteria"],
                "unmet_criteria": d["unmet_criteria"],
                "failed_conditions": d["failed_conditions"],
                "disqualifiers": d["disqualifiers"],
                "required_documents": d["required_documents"]
            }
            log_entitlement_audit(citizen_id, query_id, d["scheme_name"], action, decision_trace)
    except Exception as e:
        logger.warning("Failsafe: audit logs not saved: %s", e)



def entitlement_agent(raw_query: str, citizen_id: str | None = None, user_id: str | None = None) -> dict[str, Any]:
    """
    Synchronous orchestration entrypoint for the Entitlement Agent.

    This does not write to entitlement_queries. Use run_entitlement_check when
    the FastAPI/background-job lifecycle should persist the result.
    """
    intent = classify_intent(raw_query)
    if intent == "OUT_OF_SCOPE":
        _debug_log("intent_gating", {
            "intent_detected": "OUT_OF_SCOPE",
            "intent_confidence": 1.0,
            "query_rejected_reason": "Query is outside the scope of government schemes/entitlements",
            "pipeline_stopped_at": "intent_gating"
        })
        rejection_msg = "This query is outside the scope of the Entitlement Agent. Please ask about government schemes, eligibility, benefits, subsidies, required documents, or citizen entitlements."
        result = {
            "agent": "entitlement",
            "status": "COMPLETED",
            "citizen_id": citizen_id,
            "user_id": user_id,
            "raw_query": raw_query,
            "extracted_profile": {},
            "scheme_matches": [],
            "determination": {
                "verdict": "OUT_OF_SCOPE",
                "decision_status": "OUT_OF_SCOPE",
                "explanation": {
                    "eligibility_status": "Out of Scope",
                    "reasoning": rejection_msg,
                    "matched_conditions": [],
                    "failed_conditions": [],
                    "missing_information": [],
                    "required_documents": [],
                    "policy_citations": [],
                    "scorecard": [],
                    "confidence": 0,
                    "profile_completeness": 0,
                    "formatted": rejection_msg
                },
                "schemes": [],
                "rule_evaluation": [],
                "edge_cases": {
                    "primary_matches": [],
                    "adjacent_suggestions": [],
                    "missing_profile_fields": [],
                    "missing_documents": [],
                    "clarification_questions": [],
                    "borderline_cases": [],
                    "user_register": "standard"
                },
                "missing_documents": [],
                "adjacent_suggestions": [],
                "clarification_questions": [],
                "notes": [rejection_msg]
            }
        }
        remember_entitlement_result(result)
        return result

    conn = None
    try:
        conn = get_db_conn()
        profile = extract_profile(raw_query)
        scheme_matches, determination = build_determination(conn, raw_query, profile)
        result = {
            "agent": "entitlement",
            "status": "COMPLETED",
            "citizen_id": citizen_id,
            "user_id": user_id,
            "raw_query": raw_query,
            "extracted_profile": profile,
            "scheme_matches": scheme_matches,
            "determination": determination,
        }
        log_all_schemes_audit(citizen_id, None, determination["schemes"])
        remember_entitlement_result(result)
        return result
    except Exception as exc:
        return {
            "agent": "entitlement",
            "status": "FAILED",
            "citizen_id": citizen_id,
            "user_id": user_id,
            "raw_query": raw_query,
            "error_message": str(exc),
            "extracted_profile": {},
            "scheme_matches": [],
            "determination": {},
        }
    finally:
        release_db_conn(conn)


def update_llm_explanation_async(
    query_id: str,
    citizen_id: str | None,
    raw_query: str,
    profile: dict[str, Any],
    overall_status: str,
    determinations: list[dict[str, Any]],
    edge_cases: dict[str, Any],
):
    try:
        from app.core.database import get_db_conn, release_db_conn
        conn = get_db_conn()
        try:
            # 1. Retrieve current determination record from DB
            with conn.cursor() as cur:
                cur.execute("SELECT determination FROM entitlement_queries WHERE query_id = %s", (query_id,))
                row = cur.fetchone()
            if not row or not row[0]:
                logger.warning("Could not find determination for query_id %s in background thread", query_id)
                return

            det = row[0]
            if isinstance(det, str):
                det = json.loads(det)

            # 2. Check if overall explanation is already generated
            if det.get("explanation", {}).get("llm_generated"):
                logger.info("LLM explanation already exists for query_id %s, skipping generation", query_id)
                return

            # 3. Generate Llama3 reasonings for the top 3 optimized schemes
            optimized_plan = det.get("optimized_benefit_plan", [])
            top_3_names = {item["scheme_name"] for item in optimized_plan[:3]}

            for scheme_det in det.get("schemes", []):
                if scheme_det["scheme_name"] in top_3_names:
                    # Deduplication check: check if it already has LLM-generated flag
                    if scheme_det.get("explanation", {}).get("llm_generated"):
                        logger.info("Scheme %s already has LLM explanation, skipping", scheme_det["scheme_name"])
                        continue

                    missing_docs_list = [d.get("document") for d in scheme_det.get("missing_documents", [])] if isinstance(scheme_det.get("missing_documents"), list) else []
                    llm_reasoning = _generate_scheme_llm_explanation(
                        scheme_name=scheme_det["scheme_name"],
                        verdict=scheme_det["verdict"],
                        matched_conditions=scheme_det["met_criteria"],
                        failed_conditions=scheme_det["failed_conditions"],
                        missing_information=scheme_det["missing_information"],
                        missing_documents=missing_docs_list,
                        next_steps=scheme_det["next_steps"],
                        fallback_reasoning=scheme_det["explanation"]["reasoning"]
                    )
                    scheme_det["explanation"]["reasoning"] = llm_reasoning
                    scheme_det["explanation"]["llm_generated"] = True

            # 4. Generate overall explanation
            eligibility_status = overall_status.replace("_", " ").title()
            primary = determinations[0] if determinations else {}
            citations = primary.get("citations", [])
            
            profile_completeness_pct = _profile_completeness(profile)
            required_documents = _unique_items(
                doc
                for item in determinations
                for doc in item.get("required_documents", [])
            )
            missing_documents = edge_cases.get("missing_documents", [])
            confidence = _eligibility_confidence(
                overall_status,
                profile_completeness_pct,
                citations,
                missing_documents,
                required_documents,
            )
            
            scheme = primary.get("scheme_name", "the matching scheme")
            uncertainties = profile.get("uncertainties", [])
            
            if overall_status == "ELIGIBLE":
                reasoning = f"You appear eligible for {scheme} because your profile satisfies the required conditions."
            elif overall_status == "PENDING_DOCS":
                reasoning = f"You appear eligible for {scheme}, but we still need to verify some details or obtain required documents before confirming eligibility."
                if uncertainties:
                    unresolved = ", ".join(_field_label(u["field"]) for u in uncertainties)
                    reasoning += f" Specifically, you expressed uncertainty about: {unresolved}."
            else:
                reasoning = f"You do not appear eligible for the matched schemes due to unmet criteria or disqualifications."

            matched_conditions = _unique_items(
                condition
                for item in determinations
                for condition in item.get("met_criteria", [])
            )
            failed_conditions = _unique_items(
                condition
                for item in determinations
                for condition in item.get("failed_conditions", [])
            )
            missing_information = _friendly_fields(edge_cases.get("missing_profile_fields", []))
            scorecard = _generate_scorecard(matched_conditions, missing_information, failed_conditions)

            next_steps = []
            for u in uncertainties:
                field_label = _field_label(u["field"])
                why = u["why_required"]
                steps = " ".join(u["verification_steps"])
                q = u["question"]
                next_steps.append(f"Verify {field_label}: {why} How to check: {steps} Follow-up: {q}")
                
            uncertainty_fields = {u["field"] for u in uncertainties}
            for q in edge_cases.get("clarification_questions", []):
                next_steps.append(q)

            for doc_item in missing_documents:
                next_steps.append(f"Submit document '{doc_item['document']}' to verify {doc_item['reason']}")

            policy_citations = []
            for item in determinations:
                for citation in item.get("citations", [])[:2]:
                    policy_citations.append(citation)
            policy_citations = policy_citations[:6]

            llm_formatted = _generate_llm_explanation(
                eligibility_status,
                confidence,
                reasoning,
                scorecard,
                missing_information,
                required_documents,
                next_steps,
                policy_citations,
            )

            if llm_formatted:
                det["explanation"]["formatted"] = llm_formatted
                det["explanation"]["llm_generated"] = True

            # 5. Save updated determination and set status to COMPLETED
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE entitlement_queries 
                    SET determination = %s, status = 'COMPLETED', updated_at = NOW() 
                    WHERE query_id = %s
                    """,
                    (json.dumps(det), query_id)
                )
                conn.commit()
            logger.info("Successfully updated query_id %s with LLM explanation in background thread", query_id)

            # ------------------------------------------------------------------
            # TRIGGER GACA (Governance, Audit & Compliance Agent)
            # ------------------------------------------------------------------
            try:
                from app.agents.gaca.database import get_db
                from app.agents.gaca.schemas import GovernanceEventIn, AIMetadataIn
                from app.agents.gaca.workflow import process_event

                db_gen = get_db()
                db_session = next(db_gen)
                try:
                    # Create GACA event for top 3 schemes individually
                    for scheme_item in det.get("schemes", [])[:3]:
                        scheme_name = scheme_item.get("scheme_name", "UNKNOWN_SCHEME")
                        scheme_decision_id = f"{query_id}_{scheme_name}"
                        
                        event = GovernanceEventIn(
                            event_type="eligibility_decision",
                            responsible_agent="entitlement",
                            citizen_id=str(citizen_id) if citizen_id else "anonymous",
                            decision_id=scheme_decision_id,
                            application_id=query_id,
                            scheme_id=scheme_name,
                            decision_type="entitlement_screening",
                            decision_result=scheme_item.get("verdict", eligibility_status),
                            confidence_score=confidence,
                            policy_id=scheme_name,
                            profile_snapshot=profile,
                            retrieved_context={"citations": scheme_item.get("citations", [])},
                            required_documents=scheme_item.get("required_documents", []),
                            ai_metadata=AIMetadataIn(
                                llm="qwen-or-gemini",
                                generated_response=scheme_item.get("explanation", {}).get("reasoning", llm_formatted),
                                confidence_score=confidence
                            )
                        )
                        process_event(db_session, event)
                        logger.info("GACA Audit logged for decision_id %s", scheme_decision_id)
                finally:
                    db_session.close()
            except Exception as e:
                logger.error("Failed to push event to GACA: %s", e)

        finally:
            release_db_conn(conn)
    except Exception as e:
        logger.error("Error updating LLM explanation in background thread: %s", e)


def run_entitlement_check(query_id: str, raw_query: str, user_id: str = None, verified_docs: list[str] = None):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE entitlement_queries
                SET status = 'PROCESSING', updated_at = NOW(), error_message = NULL
                WHERE query_id = %s
                """,
                (query_id,),
            )
            conn.commit()

        intent = classify_intent(raw_query)
        if intent == "OUT_OF_SCOPE":
            _debug_log("intent_gating", {
                "intent_detected": "OUT_OF_SCOPE",
                "intent_confidence": 1.0,
                "query_rejected_reason": "Query is outside the scope of government schemes/entitlements",
                "pipeline_stopped_at": "intent_gating"
            })
            rejection_msg = "This query is outside the scope of the Entitlement Agent. Please ask about government schemes, eligibility, benefits, subsidies, required documents, or citizen entitlements."
            profile = {}
            scheme_matches = []
            determination = {
                "verdict": "OUT_OF_SCOPE",
                "decision_status": "OUT_OF_SCOPE",
                "explanation": {
                    "eligibility_status": "Out of Scope",
                    "reasoning": rejection_msg,
                    "matched_conditions": [],
                    "failed_conditions": [],
                    "missing_information": [],
                    "required_documents": [],
                    "policy_citations": [],
                    "scorecard": [],
                    "confidence": 0,
                    "profile_completeness": 0,
                    "formatted": rejection_msg
                },
                "schemes": [],
                "rule_evaluation": [],
                "edge_cases": {
                    "primary_matches": [],
                    "adjacent_suggestions": [],
                    "missing_profile_fields": [],
                    "missing_documents": [],
                    "clarification_questions": [],
                    "borderline_cases": [],
                    "user_register": "standard"
                },
                "missing_documents": [],
                "adjacent_suggestions": [],
                "clarification_questions": [],
                "notes": [rejection_msg]
            }
            
            result_for_memory = {
                "agent": "entitlement",
                "status": "COMPLETED",
                "citizen_id": None,
                "user_id": user_id,
                "raw_query": raw_query,
                "extracted_profile": profile,
                "scheme_matches": scheme_matches,
                "determination": determination,
            }
            remember_entitlement_result(result_for_memory)

            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE entitlement_queries
                    SET extracted_profile = %s,
                        scheme_matches = %s,
                        determination = %s,
                        status = 'COMPLETED',
                        updated_at = NOW()
                    WHERE query_id = %s
                    """,
                    (
                        json.dumps(profile),
                        json.dumps(scheme_matches),
                        json.dumps(determination),
                        query_id,
                    ),
                )
                conn.commit()
            return

        profile = extract_profile(raw_query)
        
        with conn.cursor() as cur:
            cur.execute("SELECT citizen_id FROM entitlement_queries WHERE query_id = %s", (query_id,))
            row = cur.fetchone()
            citizen_id = row[0] if row else None

        scheme_matches, determination = build_determination(conn, raw_query, profile, trigger_llm=False, verified_docs=verified_docs)
        
        result_for_memory = {
            "agent": "entitlement",
            "status": "GENERATING_EXPLANATION",
            "citizen_id": citizen_id,
            "user_id": user_id,
            "raw_query": raw_query,
            "extracted_profile": profile,
            "scheme_matches": scheme_matches,
            "determination": determination,
        }
        log_all_schemes_audit(citizen_id, query_id, determination["schemes"])
        remember_entitlement_result(result_for_memory)

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE entitlement_queries
                SET extracted_profile = %s,
                    scheme_matches = %s,
                    determination = %s,
                    status = 'GENERATING_EXPLANATION',
                    updated_at = NOW()
                WHERE query_id = %s
                """,
                (
                    json.dumps(profile),
                    json.dumps(scheme_matches),
                    json.dumps(determination),
                    query_id,
                ),
            )
            conn.commit()

        # Launch background thread to update explanation with Llama3 asynchronously
        threading.Thread(
            target=update_llm_explanation_async,
            args=(
                query_id,
                citizen_id,
                raw_query,
                profile,
                determination["decision_status"],
                determination["schemes"],
                determination["edge_cases"]
            ),
            daemon=True
        ).start()

    except Exception as e:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE entitlement_queries
                SET status = 'FAILED',
                    error_message = %s,
                    updated_at = NOW()
                WHERE query_id = %s
                """,
                (str(e), query_id),
            )
            conn.commit()
    finally:
        release_db_conn(conn)
