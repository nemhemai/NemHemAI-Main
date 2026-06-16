import os
import sys
import json
from pathlib import Path

# Add current directory to path so app can be imported
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.services.normalization_service import NormalizationService
from app.services.preprocessing_service import PreprocessingService
from app.services.ocr_service import OCRService
from app.services.classification_service import ClassificationService
from app.services.field_extraction_service import FieldExtractionService
from app.services.verification_service import VerificationService
from app.services.cross_validation_service import CrossValidationService
from app.services.fraud_detection_service import FraudDetectionService
from app.services.decision_service import DecisionService


def test_pipeline_on_document(file_path):
    print("\n" + "="*80)
    print(f"TESTING PIPELINE ON: {file_path}")
    print("="*80)

    # 1. Normalization
    print("\n[1] Running Normalization...")
    norm_res = NormalizationService.normalize_document(str(file_path))
    print(f"    Normalized pages: {len(norm_res['normalized_pages'])}")
    
    # 2. Preprocessing
    print("\n[2] Running Preprocessing...")
    prep_res = PreprocessingService.preprocess_document(norm_res["normalized_pages"])
    print(f"    Processed pages: {len(prep_res['processed_pages'])}")

    # 3. OCR Text Extraction
    print("\n[3] Running PaddleOCR...")
    ocr_res = OCRService.extract_text(prep_res["processed_pages"])
    raw_text = ocr_res["extracted_text"]
    print(f"    Extracted Text snippet:\n{raw_text[:200]}...")

    # 4. Document Classification
    print("\n[4] Running Classification...")
    doc_type = ClassificationService.classify(raw_text)
    print(f"    Classified Document Type: {doc_type}")

    # 5. Field Parsing
    print("\n[5] Running Field Extraction...")
    extract_res = FieldExtractionService.extract_fields(doc_type, raw_text)
    fields = extract_res["extracted_fields"]
    print(f"    Extracted Fields: {json.dumps(fields, indent=2)}")

    # 6. Verification Rules
    print("\n[6] Running Verification Rules...")
    verify_res = VerificationService.verify(doc_type, fields)
    print(f"    Verified: {verify_res['verified']}")
    print(f"    Passed checks: {verify_res['passed_checks']}")
    print(f"    Failed checks: {verify_res['failed_checks']}")

    # 7. Cross Validation (MRZ + Central Database lookup)
    print("\n[7] Running Cross Validation...")
    cross_res = CrossValidationService.cross_validate(doc_type, fields)
    print(f"    Cross-validation checks:")
    for check_name, data in cross_res.items():
        print(f"      - {check_name}: {'PASSED' if data['passed'] else 'FAILED'} | {data['detail']}")

    # Merge cross validation checks into verification result for decision input
    passed_verify = list(verify_res.get("passed_checks") or [])
    failed_verify = list(verify_res.get("failed_checks") or [])
    for check_name, data in cross_res.items():
        if data["passed"]:
            passed_verify.append(check_name)
        else:
            failed_verify.append(check_name)
    verify_res["passed_checks"] = passed_verify
    verify_res["failed_checks"] = failed_verify
    if failed_verify:
        verify_res["verified"] = False
        verify_res["overall_valid"] = False

    # 8. Fraud Detection (run on original uploaded path)
    print("\n[8] Running Fraud Detection...")
    fraud_res = FraudDetectionService.detect(str(file_path))
    print(f"    Risk level: {fraud_res['fraud_risk']} | Score: {fraud_res['fraud_score']}")
    print(f"    Fraud flags: {fraud_res['fraud_flags']}")

    # 9. Decision Aggregation
    print("\n[9] Running Decision Aggregator...")
    decision_res = DecisionService.decide(verify_res, fraud_res)
    print(f"    FINAL DECISION: {decision_res['decision']}")
    print(f"    Combined Confidence: {decision_res['confidence']}")
    print(f"    Reasons: {decision_res['reasons']}")
    
    print("\nSUCCESS: End-to-end pipeline verification completed!")


def main():
    # Make sure output directories exist
    os.makedirs("storage/uploads", exist_ok=True)
    os.makedirs("storage/normalized", exist_ok=True)
    os.makedirs("storage/processed", exist_ok=True)
    os.makedirs("storage/temp", exist_ok=True)

    aadhaar_img = Path("government_test_assets/aadhaar/images/aadhaar_0000.png")
    pan_img = Path("government_test_assets/pan/images/pan_0000.png")
    passport_img = Path("government_test_assets/passport/images/passport_0000.png")

    if aadhaar_img.exists():
        test_pipeline_on_document(aadhaar_img)
    else:
        print(f"Aadhaar test image not found at {aadhaar_img}")

    if pan_img.exists():
        test_pipeline_on_document(pan_img)
    else:
        print(f"PAN test image not found at {pan_img}")

    if passport_img.exists():
        test_pipeline_on_document(passport_img)
    else:
        print(f"Passport test image not found at {passport_img}")


if __name__ == "__main__":
    main()
