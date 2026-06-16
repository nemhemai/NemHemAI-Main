from __future__ import annotations

from typing import Any


FIELD_QUESTIONS = {
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

FIELD_LABELS = {
    "income_annual": "Annual income",
    "land_ownership_acres": "Land ownership information",
    "category": "Applicant category",
    "urban_rural": "Urban or rural location",
    "education_level": "Education level",
    "occupation": "Occupation",
    "has_aadhaar": "Aadhaar status",
    "has_bank_account": "Bank account details",
    "has_vending_certificate": "Vending certificate",
    "has_ulb_recommendation": "ULB/TVC recommendation letter",
    "has_pucca_house": "Pucca house ownership",
    "state": "State",
}

FIELD_DOCUMENTS = {
    "income_annual": "Income certificate",
    "land_ownership_acres": "Land records / ownership proof",
    "category": "Caste/category certificate",
    "urban_rural": "Address or residence proof",
    "education_level": "Admission/enrollment certificate",
    "has_aadhaar": "Aadhaar",
    "has_bank_account": "Bank account details",
    "has_vending_certificate": "Vending certificate or ULB/TVC recommendation",
    "has_ulb_recommendation": "ULB/TVC recommendation letter",
    "has_pucca_house": "No-pucca-house declaration",
    "state": "State residency proof",
}


def friendly_field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def check_edge_cases(
    raw_query: str,
    profile: dict[str, Any],
    scheme_matches: list[dict[str, Any]],
    determinations: list[dict[str, Any]],
) -> dict[str, Any]:
    missing_fields = _collect_missing_fields(determinations)
    missing_documents = _missing_documents(missing_fields, determinations)
    clarification_questions = _clarification_questions(missing_fields, raw_query, profile)
    borderline_cases = _borderline_cases(profile, determinations)
    adjacent_suggestions = _adjacent_suggestions(profile, scheme_matches)

    return {
        "primary_matches": [item["scheme_name"] for item in scheme_matches[:3]],
        "adjacent_suggestions": adjacent_suggestions,
        "missing_profile_fields": missing_fields,
        "missing_documents": missing_documents,
        "clarification_questions": clarification_questions,
        "borderline_cases": borderline_cases,
        "user_register": _user_register(raw_query, missing_fields),
    }


def _collect_missing_fields(determinations: list[dict[str, Any]]) -> list[str]:
    fields = []
    seen = set()
    for determination in determinations:
        for field in determination.get("missing_profile_fields", []):
            if field not in seen:
                fields.append(field)
                seen.add(field)
    return fields


def _missing_documents(
    missing_fields: list[str],
    determinations: list[dict[str, Any]],
) -> list[dict[str, str]]:
    docs = []
    seen = set()

    for field in missing_fields:
        doc = FIELD_DOCUMENTS.get(field)
        if doc and doc not in seen:
            docs.append({"document": doc, "reason": f"Needed to verify {friendly_field_label(field)}"})
            seen.add(doc)

    for determination in determinations:
        if determination.get("verdict") != "PENDING_DOCS":
            continue
        for doc in determination.get("required_documents", []):
            if doc not in seen:
                docs.append({"document": doc, "reason": f"Required for {determination['scheme_name']}"})
                seen.add(doc)

    return docs


def _clarification_questions(
    missing_fields: list[str],
    raw_query: str,
    profile: dict[str, Any],
) -> list[str]:
    questions = []
    lower_query = raw_query.lower()

    if profile.get("state") is None:
        questions.append("Which state are you from?")

    for field in missing_fields:
        question = FIELD_QUESTIONS.get(field)
        if question and question not in questions:
            questions.append(question)

    has_vendor_authorization = bool(profile.get("has_vending_certificate") or profile.get("has_ulb_recommendation"))
    if (
        "vendor" in lower_query
        and not has_vendor_authorization
        and not any("vending certificate" in q.lower() for q in questions)
    ):
        questions.append("Do you have a vending certificate or a letter from your ULB/TVC?")

    return questions[:6]


def _borderline_cases(profile: dict[str, Any], determinations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cases = []
    income = profile.get("income_annual")
    category = profile.get("category")

    if isinstance(income, (int, float)):
        if 225000 <= income <= 275000:
            cases.append(
                {
                    "field": "income_annual",
                    "message": "Income is close to a common 2.5L scholarship threshold; verify with income certificate.",
                    "value": income,
                }
            )
        if 95000 <= income <= 110000 and category == "OBC":
            cases.append(
                {
                    "field": "income_annual",
                    "message": "OBC scholarship income is close to the 1L threshold; verify carefully.",
                    "value": income,
                }
            )
        if 280000 <= income <= 320000:
            cases.append(
                {
                    "field": "income_annual",
                    "message": "Income is close to the EWS 3L housing threshold; request income certificate.",
                    "value": income,
                }
            )

    if any(item["scheme_name"] == "PM-KISAN" for item in determinations):
        land = profile.get("land_ownership_acres")
        if land is None:
            cases.append(
                {
                    "field": "land_ownership_acres",
                    "message": "PM-KISAN needs cultivable land ownership verification.",
                    "value": None,
                }
            )

    return cases


def _adjacent_suggestions(
    profile: dict[str, Any],
    scheme_matches: list[dict[str, Any]],
) -> list[dict[str, str]]:
    matched = {item["scheme_name"] for item in scheme_matches}
    suggestions = []

    if profile.get("occupation") == "farmer":
        if "PM-KISAN" in matched and "PM-KUSUM" not in matched:
            suggestions.append(
                {
                    "scheme_name": "PM-KUSUM",
                    "reason": "Farmer profiles eligible for income support may also need solar pump support.",
                }
            )
        if "PM-KUSUM" in matched and "PM-KISAN" not in matched:
            suggestions.append(
                {
                    "scheme_name": "PM-KISAN",
                    "reason": "Farmer solar applicants may also qualify for income support if land records are valid.",
                }
            )

    if profile.get("occupation") == "street_vendor" and "PMAY-U" not in matched:
        suggestions.append(
            {
                "scheme_name": "PMAY-U",
                "reason": "Urban livelihood applicants may also need urban housing assistance screening.",
            }
        )

    return suggestions


def _user_register(raw_query: str, missing_fields: list[str]) -> str:
    query = raw_query.lower()
    if len(missing_fields) >= 3 or any(word in query for word in ("confused", "not sure", "don't know", "dont know")):
        return "simplified"
    return "standard"
