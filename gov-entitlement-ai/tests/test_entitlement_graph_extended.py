import copy

import pytest

from app.agents import entitlement_graph as eg


def _match(profile, scheme_name):
    matches = eg.match_entitlement_graph(profile, [scheme_name])
    assert len(matches) == 1
    return matches[0]


def test_pm_kisan_fully_eligible():
    profile = {
        "occupation": "farmer",
        "land_ownership_acres": 2,
        "has_aadhaar": True,
        "has_bank_account": True,
    }
    r = _match(profile, "PM-KISAN")
    assert r["verdict"] == "LIKELY_ELIGIBLE"
    assert r["eligibility_score"] == 1.0
    assert r["application_readiness"] == "READY"
    assert len(r["criteria_details"]) == 4
    assert r["recommendation_inputs"]["matched"] == 4


def test_pm_kusum_fully_eligible():
    profile = {"occupation": "farmer", "land_ownership_acres": 5}
    r = _match(profile, "PM-KUSUM")
    assert r["verdict"] == "LIKELY_ELIGIBLE"
    assert r["eligibility_score"] == 1.0


def test_svanidhi_fully_eligible():
    profile = {
        "occupation": "street_vendor",
        "urban_rural": "urban",
        "income_annual": 100000,
        "has_vending_certificate": True,
    }
    r = _match(profile, "PM SVANidhi")
    assert r["verdict"] == "LIKELY_ELIGIBLE"
    assert r["eligibility_score"] == 1.0


def test_pmay_u_fully_eligible():
    profile = {"urban_rural": "urban", "has_pucca_house": False, "income_annual": 100000}
    r = _match(profile, "PMAY-U")
    assert r["verdict"] == "LIKELY_ELIGIBLE"
    assert r["eligibility_score"] == 1.0


def test_pmay_g_fully_eligible():
    profile = {"urban_rural": "rural", "has_pucca_house": False}
    r = _match(profile, "PM Awas Yojana")
    assert r["verdict"] == "LIKELY_ELIGIBLE"


def test_post_matric_fully_eligible():
    profile = {"education_level": "post_matric", "category": "SC", "income_annual": 200000}
    r = _match(profile, "Post-Matric Scholarship")
    assert r["verdict"] == "LIKELY_ELIGIBLE"


def test_svanidhi_missing_information_scores_fraction():
    profile = {"occupation": "street_vendor", "urban_rural": "urban", "income_annual": 100000}
    r = _match(profile, "PM SVANidhi")
    # authorization criterion should be missing -> PENDING_DOCS
    assert r["verdict"] == "PENDING_DOCS"
    assert r["eligibility_score"] == pytest.approx(3 / 4)
    assert "has_vending_certificate" in r["missing_profile_fields"]


def test_pmkisan_exclusion_does_not_change_score():
    profile = {
        "occupation": "farmer",
        "land_ownership_acres": 2,
        "has_aadhaar": True,
        "has_bank_account": True,
        "pays_income_tax": True,
    }
    r = _match(profile, "PM-KISAN")
    assert r["verdict"] == "INELIGIBLE"
    # Score is based on criteria only and should be 1.0
    assert r["eligibility_score"] == 1.0
    assert r["application_readiness"] == "DISQUALIFIED"
    assert any(d["label"] == "Income tax payer exclusion" for d in r["exclusion_details"]) or "Income tax payer exclusion" in r["disqualifiers"]


def test_missing_documents_detection_with_doc_required(monkeypatch):
    # Temporarily mark Aadhaar criterion as document-required for PM-KISAN
    orig = eg.SCHEME_GRAPHS
    new_graphs = []
    for g in orig:
        if g.scheme_name == "PM-KISAN":
            new_criteria = []
            for c in g.criteria:
                if c.criterion_id == "pmkisan_aadhaar":
                    new_c = eg.EligibilityCriterion(c.criterion_id, c.label, c.field, c.predicate, required=c.required, weight=c.weight, doc_required=True)
                else:
                    new_c = c
                new_criteria.append(new_c)
            new_graphs.append(eg.SchemeGraph(g.scheme_name, g.benefit, tuple(new_criteria), g.exclusions))
        else:
            new_graphs.append(g)

    monkeypatch.setattr(eg, "SCHEME_GRAPHS", tuple(new_graphs))

    profile = {"occupation": "farmer", "land_ownership_acres": 2, "has_bank_account": True}
    r = _match(profile, "PM-KISAN")
    assert r["verdict"] == "PENDING_DOCS"
    assert r["application_readiness"] == "NEEDS_DOCUMENTS"
    assert "has_aadhaar_document" in r["verification"]["missing_documents"]


def test_out_of_scope_profile_is_ineligible():
    profile = {"occupation": "teacher", "land_ownership_acres": 0}
    r = _match(profile, "PM-KUSUM")
    assert r["verdict"] == "INELIGIBLE"
    assert len(r["criteria_details"]) == 2
    assert any(c["result"] is False for c in r["criteria_details"]) 


def test_recommendation_inputs_features_present():
    profile = {"occupation": "farmer", "land_ownership_acres": 3, "has_aadhaar": True, "has_bank_account": True}
    r = _match(profile, "PM-KISAN")
    features = r["recommendation_inputs"]["features"]
    # referenced fields for PM-KISAN should include these keys
    assert features.get("occupation") == "farmer"
    assert features.get("land_ownership_acres") == 3
