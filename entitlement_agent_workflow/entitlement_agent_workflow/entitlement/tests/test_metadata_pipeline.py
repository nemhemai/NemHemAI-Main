import os
import sys
import pytest
from jsonschema import ValidationError
from app.core.metadata.tools import (
    build_profile_tool,
    discover_schemes_tool,
    evaluate_eligibility_tool,
    verify_documents_stub
)
from app.core.metadata.agent import run_eligibility_pipeline

# Ensure paths for dynamic EmbeddingEngine resolution are cached in tests
@pytest.fixture(scope="module")
def setup_embedding():
    yield

def test_build_profile_tool_valid():
    """Verify that build_profile_tool constructs and validates a profile correctly."""
    valid_data = {
        "citizen_id": "c_test_123",
        "age": 28,
        "income_annual": 180000,
        "state": "Maharashtra",
        "urban_rural": "urban",
        "category": "SC",
        "verified_documents": ["Aadhaar", "Bank passbook"]
    }
    profile = build_profile_tool(valid_data)
    assert profile["citizen_id"] == "c_test_123"
    assert profile["age"] == 28
    assert "Aadhaar" in profile["verified_documents"]

def test_build_profile_tool_invalid():
    """Verify that build_profile_tool raises ValidationError on invalid schemas."""
    invalid_data = {
        "age": "invalid_age_string",  # should be integer
        "income_annual": 180000
    }
    with pytest.raises(ValidationError):
        build_profile_tool(invalid_data)

def test_discover_schemes_tool(setup_embedding):
    """Verify that discover_schemes_tool retrieves potential schemes via Qdrant & Neo4j."""
    profile = {
        "citizen_id": "c_vendor",
        "occupation": "street_vendor",
        "category": "General",
        "state": "Delhi",
        "verified_documents": ["Aadhaar"]
    }
    
    # Run discovery search
    results = discover_schemes_tool(profile, query_text="loans for street vendors")
    assert len(results) > 0, "No candidate schemes found"
    
    # Check that PM SVANidhi was discovered
    scheme_ids = [s["scheme_id"] for s in results]
    assert any("svanidhi" in sid.lower() for sid in scheme_ids), "Expected PM-SVANIDHI to be discovered"

def test_evaluate_eligibility_tool():
    """Verify that evaluate_eligibility_tool pulls rules from Neo4j and returns evaluations."""
    profile = {
        "citizen_id": "c_test_pmsby",
        "age": 30,
        "income_annual": 300000,
        "verified_documents": ["Aadhaar"] # missing Bank passbook
    }
    
    # PMSBY requires Aadhaar and Bank passbook. The age rule is between 18 and 70.
    res = evaluate_eligibility_tool(profile, "PMSBY-INSURANCE")
    
    assert "status" in res
    # Since we are missing Bank passbook, it should be PENDING_DOCS or INCOMPLETE_PROFILE (due to bank account check)
    assert res["status"] in ["PENDING_DOCS", "INCOMPLETE_PROFILE"]

def test_verify_documents_stub():
    """Verify that verify_documents_stub returns mocked verified documents."""
    docs = ["Aadhaar", "Caste certificate", "Bank passbook"]
    verified = verify_documents_stub("user_even", docs)
    assert "Aadhaar" in verified
    assert "Bank Passbook" in verified
    # Caste certificate should be filtered out for even users based on stub logic
    assert "Caste Certificate" not in verified

def test_run_eligibility_pipeline_end_to_end(setup_embedding):
    """Test the full intake -> profile -> discovery -> evaluation -> verification -> reconfirmation pipeline."""
    citizen_input = {
        "citizen_id": "c_vendor_reconfirm",
        "age": 35,
        "income_annual": 120000,
        "state": "Maharashtra",
        "urban_rural": "urban",
        "occupation": "street_vendor",
        "category": "General",
        "verified_documents": ["Aadhaar"]
    }
    
    report = run_eligibility_pipeline(
        citizen_input, 
        search_query="schemes for street vendors needing loans",
        run_verification_agent=True
    )
    
    assert report["citizen_id"] == "c_vendor_reconfirm"
    assert len(report["schemes_evaluated"]) > 0
    
    # Check a scheme that should be evaluated
    assert "MUDRA-LENDING" in report["schemes_evaluated"]
    mudra_eval = report["schemes_evaluated"]["MUDRA-LENDING"]
    
    # Mudra requires Aadhaar & Business Proof. Aadhaar is in verified_documents, Business proof will be verified.
    # Initial status should be PENDING_DOCS, final status should be ELIGIBLE
    assert mudra_eval["initial_status"] == "PENDING_DOCS"
    assert mudra_eval["final_status"] == "ELIGIBLE"
    assert mudra_eval["verification_agent_run"].startswith("Completed")
