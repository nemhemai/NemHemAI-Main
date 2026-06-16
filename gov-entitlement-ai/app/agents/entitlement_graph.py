from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


Predicate = Callable[[dict[str, Any]], bool | None]


@dataclass(frozen=True)
class EligibilityCriterion:
    criterion_id: str
    label: str
    field: str
    predicate: Predicate
    # Additional metadata to ease migration and scoring. Defaults keep
    # current behaviour unchanged.
    required: bool = True
    weight: float = 1.0
    doc_required: bool = False


@dataclass(frozen=True)
class ExclusionRule:
    rule_id: str
    label: str
    field: str
    predicate: Predicate
    # Weight to allow graded exclusion impact in future scoring.
    weight: float = 1.0


@dataclass(frozen=True)
class SchemeGraph:
    scheme_name: str
    benefit: str
    criteria: tuple[EligibilityCriterion, ...]
    exclusions: tuple[ExclusionRule, ...] = ()

    def to_metadata(self) -> dict[str, Any]:
        """Export a JSON-serializable representation of this graph.

        This helper prepares the in-code graph for migration to a
        metadata-driven store. It does not change runtime behaviour.
        """
        return {
            "scheme_name": self.scheme_name,
            "benefit": self.benefit,
            "criteria": [
                {
                    "criterion_id": c.criterion_id,
                    "label": c.label,
                    "field": c.field,
                    "required": c.required,
                    "weight": c.weight,
                    "doc_required": c.doc_required,
                }
                for c in self.criteria
            ],
            "exclusions": [
                {"rule_id": e.rule_id, "label": e.label, "field": e.field, "weight": e.weight}
                for e in self.exclusions
            ],
        }


def _value(profile: dict[str, Any], field: str) -> Any:
    return profile.get(field)


def _equals(field: str, expected: Any) -> Predicate:
    def predicate(profile: dict[str, Any]) -> bool | None:
        value = _value(profile, field)
        if value is None:
            return None
        return value == expected

    return predicate


def _is_false(field: str) -> Predicate:
    def predicate(profile: dict[str, Any]) -> bool | None:
        value = _value(profile, field)
        if value is None:
            return None
        return value is False

    return predicate


def _is_true(field: str) -> Predicate:
    def predicate(profile: dict[str, Any]) -> bool | None:
        value = _value(profile, field)
        if value is None:
            return None
        return value is True

    return predicate


def _positive_number(field: str) -> Predicate:
    def predicate(profile: dict[str, Any]) -> bool | None:
        value = _value(profile, field)
        if value is None:
            return None
        return isinstance(value, (int, float)) and value > 0

    return predicate


def _income_lte(limit: int) -> Predicate:
    def predicate(profile: dict[str, Any]) -> bool | None:
        value = _value(profile, "income_annual")
        if value is None:
            return None
        return value <= limit

    return predicate


def _scholarship_income(profile: dict[str, Any]) -> bool | None:
    income = profile.get("income_annual")
    category = profile.get("category")
    if income is None or category is None:
        return None
    if category in {"SC", "ST"}:
        return income <= 250000
    if category == "OBC":
        return income <= 100000
    return False


def _street_vendor_authorization(profile: dict[str, Any]) -> bool | None:
    vending_certificate = profile.get("has_vending_certificate")
    ulb_recommendation = profile.get("has_ulb_recommendation")
    if vending_certificate is None and ulb_recommendation is None:
        return None
    return bool(vending_certificate or ulb_recommendation)


SCHEME_GRAPHS: tuple[SchemeGraph, ...] = (
    SchemeGraph(
        scheme_name="PMAY-U",
        benefit="Urban housing assistance under PMAY-U 2.0",
        criteria=(
            EligibilityCriterion("pmayu_area", "Applicant is in an urban area", "urban_rural", _equals("urban_rural", "urban")),
            EligibilityCriterion("pmayu_no_pucca", "Household does not own a pucca house", "has_pucca_house", _is_false("has_pucca_house")),
            EligibilityCriterion("pmayu_income", "Annual income is within PMAY-U income bands", "income_annual", _income_lte(1800000)),
        ),
    ),
    SchemeGraph(
        scheme_name="PM Awas Yojana",
        benefit="Rural housing assistance under PMAY-G/PM Awas Yojana",
        criteria=(
            EligibilityCriterion("pmayg_area", "Applicant is in a rural area", "urban_rural", _equals("urban_rural", "rural")),
            EligibilityCriterion("pmayg_no_pucca", "Household does not own a pucca house", "has_pucca_house", _is_false("has_pucca_house")),
        ),
        exclusions=(
            ExclusionRule("pmayg_govt_employee", "Government employee exclusion", "is_govt_employee", _is_true("is_govt_employee")),
            ExclusionRule("pmayg_income_tax", "Income tax payer exclusion", "pays_income_tax", _is_true("pays_income_tax")),
            ExclusionRule("pmayg_vehicle", "Motorized vehicle ownership exclusion", "owns_motorized_vehicle", _is_true("owns_motorized_vehicle")),
        ),
    ),
    SchemeGraph(
        scheme_name="PM SVANidhi",
        benefit="Working capital loan support for eligible street vendors",
        criteria=(
            EligibilityCriterion("svanidhi_vendor", "Applicant is a street vendor", "occupation", _equals("occupation", "street_vendor")),
            EligibilityCriterion("svanidhi_area", "Applicant is in an urban area", "urban_rural", _equals("urban_rural", "urban")),
            EligibilityCriterion("svanidhi_income", "Annual income is within PM SVANidhi limits", "income_annual", _income_lte(300000)),
            EligibilityCriterion("svanidhi_authorization", "Vending certificate or ULB/TVC recommendation is available", "has_vending_certificate", _street_vendor_authorization),
        ),
    ),
    SchemeGraph(
        scheme_name="PM-KUSUM",
        benefit="Solar pump and grid-connected solarization support for farmers",
        criteria=(
            EligibilityCriterion("kusum_farmer", "Applicant is a farmer", "occupation", _equals("occupation", "farmer")),
            EligibilityCriterion("kusum_land", "Applicant has cultivable land for solar pump/plant use", "land_ownership_acres", _positive_number("land_ownership_acres")),
        ),
    ),
    SchemeGraph(
        scheme_name="Post-Matric Scholarship",
        benefit="Post-matric education scholarship support",
        criteria=(
            EligibilityCriterion("pms_education", "Applicant is enrolled in a post-matric course", "education_level", _equals("education_level", "post_matric")),
            EligibilityCriterion("pms_category", "Applicant belongs to SC, ST, or OBC category", "category", lambda p: None if p.get("category") is None else p.get("category") in {"SC", "ST", "OBC"}),
            EligibilityCriterion("pms_income", "Parental/household income is within category threshold", "income_annual", _scholarship_income),
        ),
    ),
    SchemeGraph(
        scheme_name="PM-KISAN",
        benefit="Income support for eligible landholding farmer families",
        criteria=(
            EligibilityCriterion("pmkisan_farmer", "Applicant is a farmer", "occupation", _equals("occupation", "farmer")),
            EligibilityCriterion("pmkisan_land", "Applicant has cultivable land ownership", "land_ownership_acres", _positive_number("land_ownership_acres")),
            EligibilityCriterion("pmkisan_aadhaar", "Aadhaar is available/seeded", "has_aadhaar", _is_true("has_aadhaar")),
            EligibilityCriterion("pmkisan_bank", "Bank account is available", "has_bank_account", _is_true("has_bank_account")),
        ),
        exclusions=(
            ExclusionRule("pmkisan_institutional", "Institutional landholder exclusion", "is_institutional_landholder", _is_true("is_institutional_landholder")),
            ExclusionRule("pmkisan_govt_employee", "Government employee exclusion", "is_govt_employee", _is_true("is_govt_employee")),
            ExclusionRule("pmkisan_income_tax", "Income tax payer exclusion", "pays_income_tax", _is_true("pays_income_tax")),
        ),
    ),
)


def match_entitlement_graph(profile: dict[str, Any], scheme_names: list[str] | None = None) -> list[dict[str, Any]]:
    allowed = set(scheme_names or [])
    matches = []

    for graph in SCHEME_GRAPHS:
        if allowed and graph.scheme_name not in allowed:
            continue

        # Collect detailed criterion and exclusion evaluation results
        criteria_details: list[dict[str, Any]] = []
        exclusion_details: list[dict[str, Any]] = []

        met_criteria: list[str] = []
        unmet_criteria: list[str] = []
        missing_fields: list[str] = []
        disqualifiers: list[str] = []

        for criterion in graph.criteria:
            result = criterion.predicate(profile)
            criteria_details.append(
                {
                    "criterion_id": criterion.criterion_id,
                    "label": criterion.label,
                    "field": criterion.field,
                    "result": result,
                    "required": criterion.required,
                    "weight": criterion.weight,
                    "doc_required": criterion.doc_required,
                }
            )

            if result is True:
                met_criteria.append(criterion.label)
            elif result is False:
                unmet_criteria.append(criterion.label)
            else:
                missing_fields.append(criterion.field)

        for exclusion in graph.exclusions:
            result = exclusion.predicate(profile)
            exclusion_details.append(
                {
                    "rule_id": exclusion.rule_id,
                    "label": exclusion.label,
                    "field": exclusion.field,
                    "result": result,
                    "weight": exclusion.weight,
                }
            )
            if result is True:
                disqualifiers.append(exclusion.label)

        # Preserve original verdict behaviour for backward compatibility
        if disqualifiers or unmet_criteria:
            verdict = "INELIGIBLE"
        elif missing_fields:
            verdict = "PENDING_DOCS"
        else:
            verdict = "LIKELY_ELIGIBLE"

        # Scoring: matched criteria / total criteria (weights reserved for future use)
        total_criteria = len(graph.criteria)
        matched_count = sum(1 for c in criteria_details if c["result"] is True)
        eligibility_score = matched_count / total_criteria if total_criteria > 0 else 0.0

        # Recommendation input: canonical feature bag helpful for downstream engines
        referenced_fields = {c.field for c in graph.criteria} | {e.field for e in graph.exclusions}
        features = {f: profile.get(f) for f in referenced_fields}

        # Verification placeholders: allow Verification Agent to surface verifications, mismatches, missing docs
        verified_fields = profile.get("verified_fields", []) or []
        mismatches = [c["field"] for c in criteria_details if c["result"] is False and profile.get(c["field"]) is not None]
        missing_documents = [
            c["field"] + "_document"
            for c in criteria_details
            if c.get("doc_required") and profile.get(c["field"]) is None
        ]

        # Application readiness: an operational flag for downstream workflows
        if verdict == "LIKELY_ELIGIBLE" and not missing_fields:
            application_readiness = "READY"
        elif verdict == "LIKELY_ELIGIBLE" and missing_fields:
            application_readiness = "NEEDS_DOCUMENTS"
        elif verdict == "PENDING_DOCS":
            application_readiness = "NEEDS_DOCUMENTS"
        elif verdict == "INELIGIBLE":
            application_readiness = "DISQUALIFIED"
        else:
            application_readiness = "INCOMPLETE"

        matches.append(
            {
                "scheme_name": graph.scheme_name,
                "benefit": graph.benefit,
                "verdict": verdict,
                "met_criteria": met_criteria,
                "unmet_criteria": unmet_criteria,
                "missing_profile_fields": sorted(set(missing_fields)),
                "disqualifiers": disqualifiers,

                # New, backward-compatible enhancements for explainability and downstream use
                "criteria_details": criteria_details,
                "exclusion_details": exclusion_details,
                "eligibility_score": eligibility_score,
                "eligibility_fraction": f"{matched_count}/{total_criteria}" if total_criteria > 0 else "0/0",
                "recommendation_inputs": {"features": features, "matched": matched_count, "total": total_criteria, "score": eligibility_score},
                "verification": {
                    "verified_fields": verified_fields,
                    "mismatches": mismatches,
                    "missing_documents": missing_documents,
                },
                "application_readiness": application_readiness,
            }
        )

    return matches
