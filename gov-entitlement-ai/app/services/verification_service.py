# app/services/verification_service.py

import json
from typing import Any
import uuid
from app.core.database import get_db_conn, release_db_conn
from app.services.citizen_service import get_citizen_profile
from app.agents.entitlement_graph import match_entitlement_graph

def run_document_verification(citizen_id: str, document_type: str, file_path: str) -> dict[str, Any]:
    """
    Step 7: Verification Agent Integration.
    Simulates the Colleague's Verification Agent pipeline:
    User Uploads Document -> Classifier -> OCR -> Field Parser -> Verification Rules -> Cross Val -> Fraud -> Result
    """
    # 1. Fetch Citizen Profile to cross-validate against
    profile = get_citizen_profile(citizen_id)
    
    # 2. Classifier
    detected_type = document_type
    classification_confidence = 0.99
    
    # 3 & 4. OCR Extraction & Field Parser simulation based on profile values
    extracted_fields = {}
    ocr_confidence = 0.96
    
    if document_type == "Aadhaar":
        extracted_fields = {
            "name": profile["personal_info"].get("name", "Citizen Name"),
            "unique_id": profile["aadhaar_id"],
            "state": profile["personal_info"].get("state", "Maharashtra")
        }
    elif document_type == "Income Certificate":
        extracted_fields = {
            "name": profile["personal_info"].get("name", "Citizen Name"),
            "income_annual": profile["socio_economic_info"].get("income_annual", 250000),
            "unique_id": f"INC-{uuid.uuid4().hex[:8].upper()}"
        }
    elif document_type == "Caste/category certificate":
        extracted_fields = {
            "name": profile["personal_info"].get("name", "Citizen Name"),
            "category": profile["socio_economic_info"].get("category", "OBC"),
            "unique_id": f"CST-{uuid.uuid4().hex[:8].upper()}"
        }
    else:
        extracted_fields = {
            "name": profile["personal_info"].get("name", "Citizen Name"),
            "unique_id": f"DOC-{uuid.uuid4().hex[:8].upper()}"
        }
        
    # 5. Verification Rules
    rules_passed = ["expiry_check", "authority_signature_check"]
    rules_failed = []
    
    # 6. Cross Validation (Compare OCR fields with Profile data)
    cross_val_fields = {}
    profile_discrepancies = []
    
    if document_type == "Aadhaar":
        cross_val_fields["aadhaar_id"] = True
    elif document_type == "Income Certificate":
        profile_income = profile["socio_economic_info"].get("income_annual", 0)
        cert_income = extracted_fields.get("income_annual", 0)
        # Check matching
        match = (profile_income == cert_income)
        cross_val_fields["income_annual"] = match
        if not match:
            profile_discrepancies.append(f"Income mismatch: Profile states {profile_income}, Certificate states {cert_income}")
    elif document_type == "Caste/category certificate":
        profile_cat = profile["socio_economic_info"].get("category", "General")
        cert_cat = extracted_fields.get("category", "General")
        match = (profile_cat == cert_cat)
        cross_val_fields["category"] = match
        if not match:
            profile_discrepancies.append(f"Category mismatch: Profile states {profile_cat}, Certificate states {cert_cat}")

    # 7. Fraud Detection
    is_tampered = False
    anomaly_detected = len(profile_discrepancies) > 0
    anomaly_details = "; ".join(profile_discrepancies) if anomaly_detected else None
    risk_score = 0.75 if anomaly_detected else 0.03
    
    # 8. Verification Result
    if anomaly_detected:
        status = "REJECTED"
        reason = f"Cross-validation discrepancies found: {anomaly_details}"
        overall_confidence = 0.82
    else:
        status = "VERIFIED"
        reason = "Document classification, OCR checks, and Profile cross-validation succeeded."
        overall_confidence = 0.98

    verification_id = str(uuid.uuid4())
    verification_response = {
        "verification_id": verification_id,
        "citizen_id": citizen_id,
        "document_type": document_type,
        "document_classification": {
            "detected_type": detected_type,
            "confidence": classification_confidence
        },
        "ocr_extraction": {
            "extracted_fields": extracted_fields,
            "ocr_confidence": ocr_confidence
        },
        "field_parsing": {
            "parsed_successfully": True,
            "missing_mandatory_fields": []
        },
        "rules_evaluation": {
            "rules_passed": rules_passed,
            "rules_failed": rules_failed
        },
        "cross_validation": {
            "matched_with_profile_fields": cross_val_fields,
            "profile_discrepancies": profile_discrepancies
        },
        "fraud_detection": {
            "is_tampered": is_tampered,
            "anomaly_detected": anomaly_detected,
            "anomaly_details": anomaly_details,
            "risk_score": risk_score
        },
        "verification_result": {
            "status": status,
            "overall_confidence": overall_confidence,
            "reason": reason
        }
    }

    # Store in database
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO citizen_documents (
                    citizen_id, document_type, file_path, verification_status, 
                    ocr_extracted_data, anomaly_detected, anomaly_details
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                citizen_id, 
                document_type, 
                file_path, 
                status, 
                json.dumps(extracted_fields), 
                anomaly_detected, 
                anomaly_details
            ))
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise Exception(f"Database error saving document verification status: {e}")
    finally:
        release_db_conn(conn)

    return verification_response

def run_eligibility_reconfirmation(citizen_id: str) -> dict[str, Any]:
    """
    Step 8: Eligibility Reconfirmation.
    Consumes verified evidence package (from citizen_documents) + citizen profile + rules.
    Outputs the final eligibility status.
    """
    profile = get_citizen_profile(citizen_id)
    
    # 1. Fetch all verified documents
    conn = get_db_conn()
    verified_docs = {}
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT document_type, verification_status 
                FROM citizen_documents 
                WHERE citizen_id = %s
            """, (citizen_id,))
            rows = cur.fetchall()
            for doc_type, status in rows:
                verified_docs[doc_type] = status
    finally:
        release_db_conn(conn)

    # 2. Run graph matching rules
    # Convert Citizen Profile format to flat dict format needed by graph match
    flat_profile = {
        "state": profile["personal_info"].get("state"),
        "urban_rural": profile["personal_info"].get("urban_rural"),
        "occupation": profile["socio_economic_info"].get("occupation"),
        "income_annual": profile["socio_economic_info"].get("income_annual"),
        "category": profile["socio_economic_info"].get("category"),
        "land_ownership_acres": profile["socio_economic_info"].get("land_ownership_acres"),
        "education_level": profile["socio_economic_info"].get("education_level"),
        "has_pucca_house": profile["socio_economic_info"].get("has_pucca_house"),
        "has_aadhaar": verified_docs.get("Aadhaar") == "VERIFIED",
        "has_bank_account": profile["socio_economic_info"].get("has_bank_account", True),
        "has_vending_certificate": verified_docs.get("Vending certificate or ULB/TVC recommendation") == "VERIFIED",
    }
    
    raw_matches = match_entitlement_graph(flat_profile)
    
    reconfirmed_schemes = []
    all_eligible = True
    
    for match in raw_matches:
        scheme_name = match["scheme_name"]
        
        # Check if verdict requires documents that are missing or rejected
        verdict = match["verdict"]
        missing_fields = match["missing_profile_fields"]
        
        # Cross check verification statuses of matching required documents
        doc_status = "PENDING"
        if scheme_name == "PMAY-U":
            doc_status = verified_docs.get("No-pucca-house declaration", "PENDING")
        elif scheme_name == "PM SVANidhi":
            doc_status = verified_docs.get("Vending certificate or ULB/TVC recommendation", "PENDING")
        elif scheme_name == "PM-KISAN" or scheme_name == "PM-KUSUM":
            doc_status = verified_docs.get("Land records / ownership proof", "PENDING")
        elif scheme_name == "Post-Matric Scholarship":
            doc_status = verified_docs.get("Caste/category certificate", "PENDING")
            
        # Reconfirmation decision mapping
        if verdict == "LIKELY_ELIGIBLE" and doc_status == "VERIFIED":
            final_status = "ELIGIBLE"
        elif verdict == "INELIGIBLE":
            final_status = "INELIGIBLE"
        else:
            final_status = "PENDING_VERIFICATION"
            all_eligible = False
            
        reconfirmed_schemes.append({
            "scheme_name": scheme_name,
            "benefit": match["benefit"],
            "preliminary_verdict": verdict,
            "verification_check": doc_status,
            "final_decision": final_status
        })

    overall_decision = "ELIGIBLE" if all_eligible else "PENDING_VERIFICATION"
    
    return {
        "citizen_id": citizen_id,
        "overall_decision": overall_decision,
        "schemes": reconfirmed_schemes,
        "verified_document_checklist": verified_docs
    }
