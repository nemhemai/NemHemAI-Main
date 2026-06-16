# tests/test_entitlement_stateful.py

# pyrefly: ignore [missing-import]
import pytest
from app.services.citizen_service import register_citizen, update_citizen_profile, get_citizen_profile
from app.services.benefit_optimization_service import optimize_benefits
from app.services.verification_service import run_document_verification, run_eligibility_reconfirmation
from app.services.guidance_service import generate_guidance_data, submit_citizen_application, track_application_status
from app.services.audit_service import get_citizen_audit_logs, log_entitlement_audit
from app.core.database import get_db_conn, release_db_conn

@pytest.mark.integration
def test_full_stateful_entitlement_workflow_success(db_conn):
    """
    Test the entire 14-step workflow end-to-end using database integration.
    """
    mobile = "9876543210"
    aadhaar = "999988887777"
    email = "test@citizen.gov.in"

    # Clean up preexisting records if any
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM citizens WHERE mobile_number = %s OR aadhaar_id = %s", (mobile, aadhaar))
            conn.commit()
    finally:
        release_db_conn(conn)

    # 1. Step 1 & 2: Register citizen and run identity verification checks
    reg_res = register_citizen(mobile_number=mobile, aadhaar_id=aadhaar, email=email)
    assert reg_res["success"] is True
    assert reg_res["citizen_id"]
    assert reg_res["is_verified"] is True
    
    citizen_id = reg_res["citizen_id"]

    # 2. Step 3 & 4: Create Citizen 360 profile and Household Socio-Economic Assessment
    personal = {"name": "Murtaza Ali", "state": "Maharashtra", "urban_rural": "urban"}
    household = {"dependents_count": 3, "has_senior_citizens": False, "has_students": True, "has_widows": False}
    socio = {"income_annual": 250000, "occupation": "street_vendor", "category": "OBC", "land_ownership_acres": 0, "has_pucca_house": False}
    
    profile_res = update_citizen_profile(
        citizen_id=citizen_id,
        personal_info=personal,
        household_info=household,
        socio_economic_info=socio
    )
    assert profile_res["citizen_id"] == citizen_id
    assert profile_res["profile_360"]["personal_info"]["name"] == "Murtaza Ali"
    
    context = profile_res["eligibility_context_model"]
    assert context["bpl_apl_status"] == "APL"  # Income > 1.2L is APL in our mock
    assert context["applicant_category"] == "OBC"

    # 3. Step 9: Benefit Optimization ranking
    test_eligible = [
        {"scheme_name": "PM SVANidhi", "verdict": "LIKELY_ELIGIBLE"},
        {"scheme_name": "PMAY-U", "verdict": "PENDING_DOCS"}
    ]
    ranked = optimize_benefits(test_eligible)
    assert len(ranked) == 2
    # PMAY-U ranks first because of much higher benefit value (2.5L subsidy vs 10k loan)
    assert ranked[0]["scheme_name"] == "PMAY-U"
    assert ranked[1]["scheme_name"] == "PM SVANidhi"
    assert ranked[0]["rank"] == 1

    # 4. Step 7: Document Verification Agent OCR simulated pipeline
    verify_res = run_document_verification(
        citizen_id=citizen_id,
        document_type="Income Certificate",
        file_path="C:/documents/income_proof.pdf"
    )
    assert verify_res["verification_id"]
    assert verify_res["verification_result"]["status"] == "VERIFIED"
    assert verify_res["document_classification"]["detected_type"] == "Income Certificate"
    assert verify_res["ocr_extraction"]["extracted_fields"]["income_annual"] == 250000

    # 5. Step 8: Eligibility Reconfirmation
    reconfirm_res = run_eligibility_reconfirmation(citizen_id=citizen_id)
    assert reconfirm_res["citizen_id"] == citizen_id
    assert "Income Certificate" in reconfirm_res["verified_document_checklist"]

    # 6. Step 11: Guidance assistance and Affidavit text generation
    guide_res = generate_guidance_data(citizen_id=citizen_id, scheme_name="PM SVANidhi")
    assert guide_res["citizen_id"] == citizen_id
    assert guide_res["prefilled_form"]["applicant_name"] == "Murtaza Ali"
    assert "declare" in guide_res["affidavit_text"].lower()

    # 7. Step 12: Application Submission via channels
    submit_res = submit_citizen_application(
        citizen_id=citizen_id,
        scheme_name="PM SVANidhi",
        form_data=guide_res["prefilled_form"],
        submission_channel="API"
    )
    assert submit_res["success"] is True
    assert submit_res["application_id"]
    assert submit_res["status"] == "SUBMITTED"
    
    app_id = submit_res["application_id"]

    # 8. Step 13: Live Status Tracking
    track_res = track_application_status(application_id=app_id)
    assert track_res["application_id"] == app_id
    assert track_res["current_stage"] == "Received"
    assert len(track_res["stages"]) == 4

    # 9. Step 14: Audit Agent Compliance logging
    log_entitlement_audit(
        citizen_id=citizen_id,
        query_id=None,
        scheme_name="PM SVANidhi",
        action="RECOMMEND",
        decision_trace={"verdict": "ELIGIBLE", "reasons": ["Verified against profile"]}
    )
    
    audit_logs = get_citizen_audit_logs(citizen_id=citizen_id)
    assert len(audit_logs) >= 1
    assert audit_logs[0]["scheme_name"] == "PM SVANidhi"
    assert audit_logs[0]["action"] == "RECOMMEND"


@pytest.mark.integration
def test_citizen_registration_invalid_inputs():
    # 1. Invalid mobile
    res1 = register_citizen(mobile_number="12345", aadhaar_id="999988887777")
    assert res1["success"] is False
    assert "Invalid Mobile number format" in res1["message"]

    # 2. Invalid Aadhaar
    res2 = register_citizen(mobile_number="9876543210", aadhaar_id="12345")
    assert res2["success"] is False
    assert "Aadhaar ID must be exactly 12 digits" in res2["message"]

    # 3. Invalid Email
    res3 = register_citizen(mobile_number="9876543210", aadhaar_id="999988887777", email="invalid_email")
    assert res3["success"] is False
    assert "Invalid Email address format" in res3["message"]


@pytest.mark.integration
def test_citizen_profile_update_invalid_inputs(db_conn):
    # Register first with a valid Verhoeff Aadhaar starting with 2
    reg_res = register_citizen(mobile_number="9876543211", aadhaar_id="234567890124")
    assert reg_res["success"] is True
    citizen_id = reg_res["citizen_id"]

    try:
        # 1. Negative income
        personal = {"name": "Test User", "state": "Maharashtra", "urban_rural": "urban"}
        household = {"dependents_count": 3}
        socio = {"income_annual": -100, "occupation": "street_vendor", "category": "OBC", "land_ownership_acres": 0}
        
        with pytest.raises(Exception) as exc_info:
            update_citizen_profile(
                citizen_id=citizen_id,
                personal_info=personal,
                household_info=household,
                socio_economic_info=socio
            )
        assert "income must be a non-negative number" in str(exc_info.value)

        # 2. Negative dependents
        household_bad = {"dependents_count": -1}
        socio_ok = {"income_annual": 250000, "occupation": "street_vendor", "category": "OBC", "land_ownership_acres": 0}
        with pytest.raises(Exception) as exc_info:
            update_citizen_profile(
                citizen_id=citizen_id,
                personal_info=personal,
                household_info=household_bad,
                socio_economic_info=socio_ok
            )
        assert "Dependents count must be a non-negative number" in str(exc_info.value)

        # 3. Negative land acres
        household_ok = {"dependents_count": 3}
        socio_bad = {"income_annual": 250000, "occupation": "street_vendor", "category": "OBC", "land_ownership_acres": -2.5}
        with pytest.raises(Exception) as exc_info:
            update_citizen_profile(
                citizen_id=citizen_id,
                personal_info=personal,
                household_info=household_ok,
                socio_economic_info=socio_bad
            )
        assert "Land ownership must be a non-negative number" in str(exc_info.value)

    finally:
        # Clean up
        conn = get_db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM citizens WHERE citizen_id = %s", (citizen_id,))
                conn.commit()
        finally:
            release_db_conn(conn)

