from app.agents.entitlement_graph import match_entitlement_graph


def _match(profile, scheme_name):
    matches = match_entitlement_graph(profile, [scheme_name])
    assert len(matches) == 1
    return matches[0]


def test_pm_kisan_likely_eligible_profile():
    result = _match(
        {
            "occupation": "farmer",
            "land_ownership_acres": 2,
            "has_aadhaar": True,
            "has_bank_account": True,
        },
        "PM-KISAN",
    )

    assert result["verdict"] == "LIKELY_ELIGIBLE"
    assert not result["missing_profile_fields"]
    assert not result["disqualifiers"]


def test_pm_kisan_income_tax_exclusion():
    result = _match(
        {
            "occupation": "farmer",
            "land_ownership_acres": 2,
            "has_aadhaar": True,
            "has_bank_account": True,
            "pays_income_tax": True,
        },
        "PM-KISAN",
    )

    assert result["verdict"] == "INELIGIBLE"
    assert "Income tax payer exclusion" in result["disqualifiers"]


def test_svanidhi_requires_vendor_authorization():
    result = _match({"occupation": "street_vendor"}, "PM SVANidhi")

    assert result["verdict"] == "PENDING_DOCS"
    assert "has_vending_certificate" in result["missing_profile_fields"]


def test_post_matric_obc_income_threshold():
    result = _match(
        {
            "education_level": "post_matric",
            "category": "OBC",
            "income_annual": 150000,
        },
        "Post-Matric Scholarship",
    )

    assert result["verdict"] == "INELIGIBLE"
    assert "Parental/household income is within category threshold" in result["unmet_criteria"]
