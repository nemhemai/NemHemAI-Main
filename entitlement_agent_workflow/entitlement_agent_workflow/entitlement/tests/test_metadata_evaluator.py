import pytest
from jsonschema import ValidationError
from app.core.metadata.schemas.validator import validate_scheme, validate_citizen
from app.core.metadata.evaluator.evaluator import (
    evaluate_operator,
    get_nested_value,
    evaluate_scheme_eligibility,
)

# Test Schemas Validation
def test_schema_validation():
    # Valid Scheme Metadata
    valid_scheme = {
        "scheme_id": "TEST-SCHEME-1",
        "scheme_name": "Test Scheme One",
        "jurisdiction": "central",
        "eligibility_rules": [
            {"field": "age", "operator": "gte", "value": 18},
            {"field": "income_annual", "operator": "lte", "value": 250000, "is_exclusion": False}
        ],
        "required_documents": ["Aadhaar", "Income certificate"]
    }
    # Should not raise any error
    validate_scheme(valid_scheme)

    # Invalid Scheme Metadata (missing required field)
    invalid_scheme = {
        "scheme_id": "TEST-SCHEME-2",
        "eligibility_rules": []
    }
    with pytest.raises(ValidationError):
        validate_scheme(invalid_scheme)

    # Valid Citizen Profile
    valid_citizen = {
        "citizen_id": "c12345",
        "age": 25,
        "income_annual": 150000,
        "state": "Maharashtra",
        "verified_documents": ["Aadhaar"]
    }
    validate_citizen(valid_citizen)

    # Invalid Citizen Profile (invalid enum value)
    invalid_citizen = {
        "category": "INVALID_CATEGORY"
    }
    with pytest.raises(ValidationError):
        validate_citizen(invalid_citizen)


# Test Nested Value Resolver
def test_get_nested_value():
    profile = {
        "personal_info": {"age": 30, "gender": "female"},
        "income_annual": 120000,
        "household": None
    }
    assert get_nested_value(profile, "personal_info.age") == 30
    assert get_nested_value(profile, "personal_info.gender") == "female"
    assert get_nested_value(profile, "income_annual") == 120000
    assert get_nested_value(profile, "personal_info.missing") is None
    assert get_nested_value(profile, "household.some_field") is None


# Test Dynamic Operator Evaluation
def test_evaluate_operator():
    # String equality
    assert evaluate_operator("Maharashtra", "eq", "Maharashtra") is True
    assert evaluate_operator("maharashtra", "eq", "MAHARASHTRA") is True  # case insensitive
    assert evaluate_operator("Mumbai", "neq", "Pune") is True

    # Numeric comparison
    assert evaluate_operator(25, "gt", 18) is True
    assert evaluate_operator("25", "gt", 18) is True  # type coercion string to float
    assert evaluate_operator(18, "lte", 18) is True
    assert evaluate_operator(15, "lt", 18) is True

    # In collection
    assert evaluate_operator("OBC", "in", ["SC", "ST", "OBC"]) is True
    assert evaluate_operator("obc", "in", ["SC", "ST", "OBC"]) is True  # case insensitive normalized
    assert evaluate_operator("General", "in", ["SC", "ST", "OBC"]) is False

    # Between range
    assert evaluate_operator(150000, "between", [100000, 200000]) is True
    assert evaluate_operator(50000, "between", [100000, 200000]) is False

    # Handle None or invalid types gracefully
    assert evaluate_operator(None, "eq", "anything") is False
    assert evaluate_operator("not_a_number", "lt", 18) is False


# Test Dynamic 4-State Scheme Eligibility Evaluation
def test_evaluate_scheme_eligibility():
    scheme = {
        "scheme_id": "PMAY-U-TEST",
        "scheme_name": "PMAY Urban test",
        "eligibility_rules": [
            {"field": "urban_rural", "operator": "eq", "value": "urban"},
            {"field": "income_annual", "operator": "lte", "value": 180000},
            {"field": "is_govt_employee", "operator": "eq", "value": True, "is_exclusion": True}
        ],
        "required_documents": ["Aadhaar", "Income certificate"]
    }

    # Case A: ELIGIBLE (All rules pass, all docs verified)
    profile_eligible = {
        "urban_rural": "urban",
        "income_annual": 150000,
        "is_govt_employee": False,
        "verified_documents": ["Aadhaar", "Income Certificate"]
    }
    res = evaluate_scheme_eligibility(profile_eligible, scheme)
    assert res["status"] == "ELIGIBLE"

    # Case B: PENDING_DOCS (All rules pass, some docs missing)
    profile_pending_docs = {
        "urban_rural": "urban",
        "income_annual": 150000,
        "is_govt_employee": False,
        "verified_documents": ["Aadhaar"]
    }
    res = evaluate_scheme_eligibility(profile_pending_docs, scheme)
    assert res["status"] == "PENDING_DOCS"
    assert "Income certificate" in res["missing_documents"]

    # Case C: INELIGIBLE (Normal eligibility rule fails)
    profile_ineligible = {
        "urban_rural": "rural", # rural instead of urban
        "income_annual": 150000,
        "is_govt_employee": False,
        "verified_documents": ["Aadhaar", "Income certificate"]
    }
    res = evaluate_scheme_eligibility(profile_ineligible, scheme)
    assert res["status"] == "INELIGIBLE"

    # Case C2: INELIGIBLE (Exclusion rule matches)
    profile_disqualified = {
        "urban_rural": "urban",
        "income_annual": 150000,
        "is_govt_employee": True, # disqualified!
        "verified_documents": ["Aadhaar", "Income certificate"]
    }
    res = evaluate_scheme_eligibility(profile_disqualified, scheme)
    assert res["status"] == "INELIGIBLE"

    # Case D: INCOMPLETE_PROFILE (Missing field)
    profile_incomplete = {
        "urban_rural": "urban",
        # "income_annual" is missing
        "is_govt_employee": False,
        "verified_documents": ["Aadhaar", "Income certificate"]
    }
    res = evaluate_scheme_eligibility(profile_incomplete, scheme)
    assert res["status"] == "INCOMPLETE_PROFILE"
    assert "income_annual" in res["missing_fields"]
