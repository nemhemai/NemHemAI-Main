import os
import sys
import pytest
from fastapi.testclient import TestClient

from app.core.metadata.api import app
from app.core.metadata.keycloak_auth import KeycloakValidator
from app.core.metadata.openhuman import OpenHumanContext

client = TestClient(app)

# Cache CWD for tests loading FlagEmbedding models
@pytest.fixture(scope="module")
def setup_embedding_path():
    yield

def test_jwt_mock_validation():
    """Verify that KeycloakValidator mock tokens can be correctly generated, signed, and validated offline."""
    citizen_id = "c_test_citizen_1"
    roles = ["CITIZEN"]
    token = KeycloakValidator.generate_mock_token(citizen_id, roles, username="test_citizen")
    
    payload = KeycloakValidator.validate_token(token)
    assert payload["sub"] == citizen_id
    assert "realm_access" in payload
    assert roles == payload["realm_access"]["roles"]

def test_role_gating_evaluate_citizen(setup_embedding_path):
    """Verify access gating rules on evaluate route."""
    citizen_id = "040bab2a-75f3-419a-ab73-bb6e67314b7d" # Murtaza Ali's UUID from PostgreSQL
    
    # 1. Generate CITIZEN token for Murtaza
    citizen_token = KeycloakValidator.generate_mock_token(citizen_id, ["CITIZEN"])
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    
    # Evaluate request payload
    payload = {
        "citizen_data": {
            "citizen_id": citizen_id,
            "age": 35,
            "income_annual": 120000,
            "state": "Maharashtra",
            "urban_rural": "urban",
            "occupation": "street_vendor",
            "category": "General",
            "verified_documents": ["Aadhaar"]
        },
        "search_query": "loan schemes"
    }
    
    # Case A: Citizen queries their own profile -> Should succeed (200 OK)
    response = client.post("/api/entitlement/evaluate", json=payload, headers=headers_citizen)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["role"] == "CITIZEN"

    # Case B: Citizen queries another citizen's profile -> Should fail (403 Forbidden)
    payload_other = payload.copy()
    payload_other["citizen_data"] = payload["citizen_data"].copy()
    payload_other["citizen_data"]["citizen_id"] = "another-citizen-uuid"
    
    response = client.post("/api/entitlement/evaluate", json=payload_other, headers=headers_citizen)
    assert response.status_code == 403

    # Case C: Officer queries another citizen's profile -> Should succeed (200 OK)
    officer_token = KeycloakValidator.generate_mock_token("officer_id", ["OFFICER"])
    headers_officer = {"Authorization": f"Bearer {officer_token}"}
    
    response = client.post("/api/entitlement/evaluate", json=payload_other, headers=headers_officer)
    assert response.status_code == 200
    assert response.json()["role"] == "OFFICER"

def test_role_gating_profile():
    """Verify profile route access rules."""
    citizen_id = "040bab2a-75f3-419a-ab73-bb6e67314b7d"
    
    citizen_token = KeycloakValidator.generate_mock_token(citizen_id, ["CITIZEN"])
    headers_citizen = {"Authorization": f"Bearer {citizen_token}"}
    
    # Case A: Citizen requests own profile -> Should succeed (200 OK)
    response = client.get(f"/api/entitlement/profile/{citizen_id}", headers=headers_citizen)
    assert response.status_code == 200
    assert response.json()["citizen_id"] == citizen_id
    
    # Case B: Citizen requests another profile -> Should fail (403 Forbidden)
    response = client.get("/api/entitlement/profile/another-uuid", headers=headers_citizen)
    assert response.status_code == 403
    
    # Case C: Officer requests any profile -> Should succeed (200 OK)
    officer_token = KeycloakValidator.generate_mock_token("officer_uuid", ["OFFICER"])
    headers_officer = {"Authorization": f"Bearer {officer_token}"}
    response = client.get(f"/api/entitlement/profile/{citizen_id}", headers=headers_officer)
    assert response.status_code == 200

def test_role_gating_admin():
    """Verify that only users with ADMIN role can submit scheme metadata."""
    citizen_token = KeycloakValidator.generate_mock_token("citizen_uuid", ["CITIZEN"])
    officer_token = KeycloakValidator.generate_mock_token("officer_uuid", ["OFFICER"])
    admin_token = KeycloakValidator.generate_mock_token("admin_uuid", ["ADMIN"])
    
    payload = {
        "scheme_metadata": {
            "scheme_id": "TEST-ADMIN-GATE",
            "scheme_name": "Admin Gate Test Scheme",
            "jurisdiction": "central",
            "eligibility_rules": [],
            "required_documents": []
        }
    }
    
    # Citizen -> 403 Forbidden
    response = client.post("/api/entitlement/admin/metadata", json=payload, headers={"Authorization": f"Bearer {citizen_token}"})
    assert response.status_code == 403
    
    # Officer -> 403 Forbidden
    response = client.post("/api/entitlement/admin/metadata", json=payload, headers={"Authorization": f"Bearer {officer_token}"})
    assert response.status_code == 403
    
    # Admin -> 201 Created
    try:
        response = client.post("/api/entitlement/admin/metadata", json=payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 201
        assert response.json()["status"] == "success"
    finally:
        record_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "core", "metadata", "records", "TEST-ADMIN-GATE.yaml")
        if os.path.exists(record_path):
            os.remove(record_path)

def test_openhuman_intent_modeling():
    """Verify that OpenHuman correctly classifies user session intents."""
    ctx = OpenHumanContext()
    session_id = "session_1"
    
    # Vague query -> CONFUSED
    assert ctx.detect_intent(session_id, "help me out") == "CONFUSED"
    
    # Document keyword -> MISSING_DOCS
    assert ctx.detect_intent(session_id, "I lost my caste certificate") == "MISSING_DOCS"
    
    # Save interaction to session
    ctx.add_interaction(session_id, "loans for street vendors", "Mudra and PM Svanidhi are available.")
    
    # Same query repeated -> REPEAT_QUERY
    assert ctx.detect_intent(session_id, "loans for street vendors") == "REPEAT_QUERY"
    
    # Vague inquiry -> GENERAL_INQUIRY
    assert ctx.detect_intent(session_id, "agricultural scheme rules") == "GENERAL_INQUIRY"

def test_openhuman_edge_case_detection():
    """Verify that PENDING_DOCS with exactly one missing document is promoted to LIKELY_ELIGIBLE."""
    ctx = OpenHumanContext()
    
    mock_report = {
        "schemes_evaluated": {
            "SCHEME-1": {
                "scheme_name": "Scheme One",
                "final_status": "PENDING_DOCS",
                "missing_documents": ["Caste Certificate"] # exactly 1 doc missing
            },
            "SCHEME-2": {
                "scheme_name": "Scheme Two",
                "final_status": "PENDING_DOCS",
                "missing_documents": ["Aadhaar", "Income Certificate"] # 2 docs missing
            }
        }
    }
    
    updated_report, alerts = ctx.detect_edge_cases(mock_report)
    
    # SCHEME-1 has 1 missing doc -> Promoted to LIKELY_ELIGIBLE
    assert updated_report["schemes_evaluated"]["SCHEME-1"]["final_status"] == "LIKELY_ELIGIBLE"
    assert "proactive_prompt" in updated_report["schemes_evaluated"]["SCHEME-1"]
    assert len(alerts) == 1
    assert "Caste Certificate" in alerts[0]
    
    # SCHEME-2 has 2 missing docs -> Unchanged
    assert updated_report["schemes_evaluated"]["SCHEME-2"]["final_status"] == "PENDING_DOCS"

def test_openhuman_tone_adaptation():
    """Verify that role-based instructions differ between Citizen, Officer, and Admin."""
    ctx = OpenHumanContext()
    
    citizen_inst = ctx.get_tone_instructions("CITIZEN")
    officer_inst = ctx.get_tone_instructions("OFFICER")
    admin_inst = ctx.get_tone_instructions("ADMIN")
    
    assert "warm" in citizen_inst.lower() or "friendly" in citizen_inst.lower()
    assert "formal" in officer_inst.lower() or "professional" in officer_inst.lower()
    assert "system" in admin_inst.lower() or "summary" in admin_inst.lower()
