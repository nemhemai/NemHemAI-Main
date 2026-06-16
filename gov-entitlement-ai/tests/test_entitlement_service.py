from app.services.entitlement_service import _candidate_rules, entitlement_agent, extract_profile


def _candidate_names(raw_query: str) -> list[str]:
    profile = extract_profile(raw_query)
    return [rule.scheme_name for rule in _candidate_rules(raw_query, profile)]


def test_extracts_farmer_profile_from_raw_query():
    profile = extract_profile(
        "I am a farmer with 2 acres cultivable land, Aadhaar and bank account."
    )

    assert profile["occupation"] == "farmer"
    assert profile["land_ownership_acres"] == 2
    assert profile["has_aadhaar"] is True
    assert profile["has_bank_account"] is True


def test_extracts_student_profile_and_income():
    profile = extract_profile(
        "I am an SC student in class 11 and family income is 2 lakh per year."
    )

    assert profile["occupation"] == "student"
    assert profile["category"] == "SC"
    assert profile["education_level"] == "post_matric"
    assert profile["income_annual"] == 200000


def test_short_category_keywords_do_not_match_inside_other_words():
    candidates = _candidate_names(
        "I am an urban street vendor with a vending certificate and need a working capital loan."
    )

    assert candidates == ["PM SVANidhi", "PMAY-U"]
    assert "Post-Matric Scholarship" not in candidates


def test_entitlement_agent_returns_orchestration_contract(monkeypatch):
    def fake_build_determination(conn, raw_query, profile):
        return (
            [{"scheme_name": "PM SVANidhi", "scheme_category": "urban_livelihood"}],
            {
                "verdict": "LIKELY_ELIGIBLE",
                "schemes": [
                    {
                        "scheme_name": "PM SVANidhi",
                        "verdict": "LIKELY_ELIGIBLE",
                        "citations": [{"chunk_id": "31_c0001"}],
                    }
                ],
            },
        )

    monkeypatch.setattr("app.services.entitlement_service.get_db_conn", lambda: object())
    monkeypatch.setattr("app.services.entitlement_service.release_db_conn", lambda conn: None)
    monkeypatch.setattr("app.services.entitlement_service.build_determination", fake_build_determination)
    monkeypatch.setattr("app.services.entitlement_service.remember_entitlement_result", lambda result: None)

    result = entitlement_agent(
        "I am an urban street vendor with a vending certificate and need a working capital loan.",
        citizen_id="citizen-1",
        user_id="user-1",
    )

    assert result["agent"] == "entitlement"
    assert result["status"] == "COMPLETED"
    assert result["citizen_id"] == "citizen-1"
    assert result["user_id"] == "user-1"
    assert result["extracted_profile"]["occupation"] == "street_vendor"
    assert result["scheme_matches"][0]["scheme_name"] == "PM SVANidhi"
    assert result["determination"]["schemes"][0]["citations"]


def test_intent_gating_layer():
    from app.services.entitlement_service import classify_intent

    assert classify_intent("What is React Context API?") == "OUT_OF_SCOPE"
    assert classify_intent("Who won yesterday's IPL match?") == "OUT_OF_SCOPE"
    assert classify_intent("What is NVIDIA stock price?") == "OUT_OF_SCOPE"
    assert classify_intent("Am I eligible for PM-KISAN?") == "Continue"
    assert classify_intent("What documents are required for PM-KISAN?") == "Continue"


def test_entitlement_agent_stops_on_out_of_scope(monkeypatch):
    called_extract = False

    def fake_extract_profile(raw_query):
        nonlocal called_extract
        called_extract = True
        return {}

    monkeypatch.setattr("app.services.entitlement_service.extract_profile", fake_extract_profile)
    monkeypatch.setattr("app.services.entitlement_service.get_db_conn", lambda: object())
    monkeypatch.setattr("app.services.entitlement_service.release_db_conn", lambda conn: None)
    monkeypatch.setattr("app.services.entitlement_service.remember_entitlement_result", lambda result: None)

    result = entitlement_agent("What is React Context API?")

    assert result["status"] == "COMPLETED"
    assert result["determination"]["verdict"] == "OUT_OF_SCOPE"
    assert "outside the scope" in result["determination"]["explanation"]["reasoning"]
    assert not called_extract

