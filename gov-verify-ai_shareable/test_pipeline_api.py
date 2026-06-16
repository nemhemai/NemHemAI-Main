"""
Quick test script for the /verify-pipeline endpoint.
Uploads a test Aadhaar image and prints the full pipeline result.
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

def test_pipeline(image_path):
    print(f"Testing pipeline with: {image_path}")
    print("=" * 60)
    
    with open(image_path, "rb") as f:
        files = {"file": (image_path.split("\\")[-1], f, "image/png")}
        resp = requests.post(f"{BASE_URL}/verify-pipeline", files=files, timeout=600)
    
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"ERROR: {resp.text}")
        return False
    
    data = resp.json()
    
    print(f"Pipeline Status: {data.get('status')}")
    print(f"Document Type: {data.get('document_type')}")
    print(f"Decision: {data.get('decision_result', {}).get('decision')}")
    print(f"Confidence: {data.get('decision_result', {}).get('confidence')}")
    print(f"Fraud Risk: {data.get('fraud_result', {}).get('fraud_risk')}")
    print(f"Fraud Score: {data.get('fraud_result', {}).get('fraud_score')}")
    print(f"Fraud Flags: {data.get('fraud_result', {}).get('fraud_flags')}")
    print(f"Extracted Fields: {json.dumps(data.get('extracted_fields', {}), indent=2)}")
    print(f"Verified: {data.get('verification_result', {}).get('verified')}")
    print(f"Passed Checks: {data.get('verification_result', {}).get('passed_checks')}")
    print(f"Failed Checks: {data.get('verification_result', {}).get('failed_checks')}")
    print(f"Cross Validation: {json.dumps(data.get('cross_validation_result', {}), indent=2)}")
    print(f"Normalized Image: {data.get('normalized_image_path')}")
    print(f"Preprocessed Image: {data.get('preprocessed_image_path')}")
    print()
    
    reasons = data.get("decision_result", {}).get("reasons", [])
    if reasons:
        print("Decision Reasons:")
        for r in reasons:
            print(f"  - {r}")
    
    return True

if __name__ == "__main__":
    image_path = sys.argv[1] if len(sys.argv) > 1 else r"government_test_assets\aadhaar\images\aadhaar_0000.png"
    success = test_pipeline(image_path)
    print()
    print("RESULT:", "PASS" if success else "FAIL")
