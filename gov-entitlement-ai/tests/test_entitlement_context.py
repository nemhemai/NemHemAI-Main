from app.agents.entitlement_context import check_edge_cases


def test_context_generates_missing_documents_and_questions():
    result = check_edge_cases(
        "I am a street vendor and need a loan.",
        {"occupation": "street_vendor"},
        [{"scheme_name": "PM SVANidhi"}],
        [
            {
                "scheme_name": "PM SVANidhi",
                "verdict": "PENDING_DOCS",
                "missing_profile_fields": ["has_vending_certificate", "has_bank_account"],
                "required_documents": ["Vending certificate or ULB/TVC recommendation", "Bank account details"],
            }
        ],
    )

    documents = {item["document"] for item in result["missing_documents"]}
    assert "Vending certificate or ULB/TVC recommendation" in documents
    assert "Bank account details" in documents
    assert any("vending certificate" in question.lower() for question in result["clarification_questions"])


def test_context_adds_farmer_adjacent_suggestion():
    result = check_edge_cases(
        "I am a farmer and get PM-KISAN.",
        {"occupation": "farmer"},
        [{"scheme_name": "PM-KISAN"}],
        [{"scheme_name": "PM-KISAN", "verdict": "LIKELY_ELIGIBLE", "missing_profile_fields": []}],
    )

    assert result["adjacent_suggestions"] == [
        {
            "scheme_name": "PM-KUSUM",
            "reason": "Farmer profiles eligible for income support may also need solar pump support.",
        }
    ]


def test_context_flags_borderline_income():
    result = check_edge_cases(
        "My income is 2.4 lakh and I need scholarship.",
        {"income_annual": 240000, "category": "SC"},
        [{"scheme_name": "Post-Matric Scholarship"}],
        [{"scheme_name": "Post-Matric Scholarship", "verdict": "LIKELY_ELIGIBLE", "missing_profile_fields": []}],
    )

    assert result["borderline_cases"]
    assert result["borderline_cases"][0]["field"] == "income_annual"
