import pytest
from fastapi.testclient import TestClient
from app.core.metadata.api import app
from app.core.metadata.keycloak_auth import require_citizen

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_dependencies():
    def override_require_citizen():
        return {
            "sub": "mock_citizen_id",
            "realm_access": {"roles": ["CITIZEN"]},
            "preferred_username": "mock_citizen"
        }
    app.dependency_overrides[require_citizen] = override_require_citizen
    yield
    app.dependency_overrides.pop(require_citizen, None)

# Define 5 personas matching Day 7 plan
PERSONAS = {
    "perfect_vendor": {
        "citizen_id": "test_perfect_vendor",
        "age": 35,
        "gender": "Female",
        "state": "Maharashtra",
        "district": "Mumbai",
        "urban_rural": "urban",
        "income_annual": 80000,
        "category": "OBC",
        "occupation": "street_vendor",
        "has_aadhaar": True,
        "has_bank_account": True,
        "has_vending_certificate": True,
        "verified_documents": ["Aadhaar", "Bank passbook", "Vending certificate or ULB recommendation"]
    },
    "missing_doc_vendor": {
        "citizen_id": "test_missing_doc_vendor",
        "age": 42,
        "gender": "Male",
        "state": "Delhi",
        "district": "Central Delhi",
        "urban_rural": "urban",
        "income_annual": 90000,
        "category": "General",
        "occupation": "street_vendor",
        "has_aadhaar": True,
        "has_bank_account": True,
        "has_vending_certificate": False,
        "verified_documents": ["Aadhaar", "Bank passbook"]
    },
    "perfect_farmer": {
        "citizen_id": "test_perfect_farmer",
        "age": 50,
        "gender": "Male",
        "state": "Punjab",
        "district": "Ludhiana",
        "urban_rural": "rural",
        "income_annual": 120000,
        "category": "SC",
        "occupation": "farmer",
        "land_ownership_acres": 2.5,
        "is_govt_employee": False,
        "pays_income_tax": False,
        "is_institutional_landholder": False,
        "has_aadhaar": True,
        "has_bank_account": True,
        "verified_documents": ["Aadhaar", "Bank passbook", "Land ownership proof"]
    },
    "wealthy_farmer": {
        "citizen_id": "test_wealthy_farmer",
        "age": 55,
        "gender": "Female",
        "state": "Haryana",
        "district": "Karnal",
        "urban_rural": "rural",
        "income_annual": 800000,
        "category": "General",
        "occupation": "farmer",
        "land_ownership_acres": 15.0,
        "is_govt_employee": False,
        "pays_income_tax": True, # Excluded!
        "is_institutional_landholder": False,
        "has_aadhaar": True,
        "has_bank_account": True,
        "verified_documents": ["Aadhaar", "Bank passbook", "Land ownership proof"]
    },
    "generic_student": {
        "citizen_id": "test_generic_student",
        "age": 20,
        "gender": "Male",
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "urban_rural": "urban",
        "income_annual": 0,
        "category": "General",
        "occupation": "student",
        "education_level": "Undergraduate",
        "has_aadhaar": True,
        "verified_documents": ["Aadhaar"]
    }
}

@pytest.fixture
def mock_load_citizen_profile(monkeypatch):
    def mock_load(citizen_id_or_aadhaar):
        # Find the persona matching the id
        for key, p in PERSONAS.items():
            if p["citizen_id"] == citizen_id_or_aadhaar:
                return p
        raise ValueError("Profile not found")
    
    # Import the function so monkeypatch works on where it is used
    import app.core.metadata.api
    import app.core.metadata.tools
    monkeypatch.setattr(app.core.metadata.api, "load_citizen_profile_from_db", mock_load)
    monkeypatch.setattr(app.core.metadata.tools, "load_citizen_profile_from_db", mock_load)


def test_perfect_vendor(mock_load_citizen_profile):
    response = client.post(
        "/api/v1/entitlement",
        json={"citizen_id": "test_perfect_vendor", "raw_query": "I am a street vendor looking for a loan."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "PM SVANidhi" in [s["scheme_name"] for s in data["schemes"]]
    # It should be READY
    svanidhi = next(s for s in data["schemes"] if "SVANidhi" in s["scheme_name"])
    assert svanidhi["application_readiness"] == "READY"

def test_missing_doc_vendor(mock_load_citizen_profile):
    response = client.post(
        "/api/v1/entitlement",
        json={"citizen_id": "test_missing_doc_vendor", "raw_query": "I am a street vendor looking for a loan."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "PM SVANidhi" in [s["scheme_name"] for s in data["schemes"]]
    svanidhi = next(s for s in data["schemes"] if "SVANidhi" in s["scheme_name"])
    assert svanidhi["application_readiness"] in ["NEEDS_VERIFICATION", "MISSING_DOCUMENTS"]

def test_perfect_farmer(mock_load_citizen_profile):
    response = client.post(
        "/api/v1/entitlement",
        json={"citizen_id": "test_perfect_farmer", "raw_query": "I am a farmer needing support."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Pradhan Mantri Kisan Samman Nidhi" in [s["scheme_name"] for s in data["schemes"]]
    kisan = next(s for s in data["schemes"] if "Kisan" in s["scheme_name"])
    assert kisan["application_readiness"] == "READY"

def test_wealthy_farmer(mock_load_citizen_profile):
    response = client.post(
        "/api/v1/entitlement",
        json={"citizen_id": "test_wealthy_farmer", "raw_query": "I am a farmer needing support."}
    )
    assert response.status_code == 200
    data = response.json()
    
    # Might not even be evaluated if excluded by pre-screening, or will be NOT_ELIGIBLE
    if data["schemes"]:
        kisan = next((s for s in data["schemes"] if "Kisan" in s["scheme_name"]), None)
        if kisan:
            assert kisan["application_readiness"] == "NOT_ELIGIBLE"
            
def test_generic_student(mock_load_citizen_profile):
    response = client.post(
        "/api/v1/entitlement",
        json={"citizen_id": "test_generic_student", "raw_query": "I am a student looking for help."}
    )
    assert response.status_code == 200
    data = response.json()
    # Shouldn't be eligible for SVANidhi or KISAN
    assert not any(s["application_readiness"] == "READY" for s in data["schemes"] if "SVANidhi" in s["scheme_name"] or "Kisan" in s["scheme_name"])
