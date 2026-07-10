import os
import traceback
from fastapi import APIRouter, File, UploadFile, Body, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from app.agents.verification.schemas.schemas import (
    OCRRequest,
    OCRResponse,
    FieldExtractionRequest,
    FieldExtractionResponse,
    VerificationRequest,
    VerificationResponse,
    FraudDetectionRequest,
    FraudDetectionResponse,
    DecisionRequest,
    DecisionResponse,
    PreprocessingRequest,
    PreprocessingResponse,
    NormalizationResponse,
    UploadResponse,
    PipelineResponse
)

from app.agents.verification.services.ingestion_service import IngestionService
from app.agents.verification.services.normalization_service import NormalizationService
from app.agents.verification.services.preprocessing_service import PreprocessingService
from app.agents.verification.services.ocr_service import OCRService
from app.agents.verification.services.classification_service import ClassificationService
from app.agents.verification.services.field_extraction_service import FieldExtractionService
from app.agents.verification.services.verification_service import VerificationService
from app.agents.verification.services.cross_validation_service import CrossValidationService
from app.agents.verification.services.fraud_detection_service import FraudDetectionService
from app.agents.verification.services.decision_service import DecisionService


router = APIRouter()


# =========================================
# UI SERVE ROUTE
# =========================================

@router.get("/", response_class=HTMLResponse)
async def get_ui():
    template_path = os.path.join("app", "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Verify UI Template not found inside app/templates/index.html</h1>"


# =========================================
# FILE RETRIEVAL STORAGE ROUTE
# =========================================

@router.get("/storage/{category}/{filename}")
async def get_storage_file(category: str, filename: str):
    file_path = os.path.join("storage", category, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return JSONResponse(status_code=404, content={"message": "File not found"})


# =========================================
# UNIFIED PIPELINE ROUTE
# =========================================

@router.post(
    "/verify-pipeline",
    response_model=PipelineResponse
)
async def verify_pipeline(
    file: UploadFile = File(...),
    profile_data: str = Form(None)
):
    try:
        # 1. Ingest uploaded file
        upload_res = await IngestionService.process_upload(file)
        file_path = os.path.abspath(upload_res["file_path"])
        filename = upload_res["filename"]
        
        # 2. Normalization (convert to standard image pages)
        norm_res = NormalizationService.normalize_document(file_path)
        normalized_pages = norm_res["normalized_pages"]
        normalized_image_path = normalized_pages[0]["normalized_path"] if normalized_pages else None
        if normalized_image_path:
            normalized_image_path = os.path.abspath(normalized_image_path)
        
        # 3. Preprocessing (denoising, contrast boost, adaptive thresholding)
        prep_res = PreprocessingService.preprocess_document(normalized_pages)
        processed_pages = prep_res["processed_pages"]
        preprocessed_image_path = processed_pages[0]["processed_path"] if processed_pages else None
        if preprocessed_image_path:
            preprocessed_image_path = os.path.abspath(preprocessed_image_path)
        
        # 4. OCR Text Extraction (PaddleOCR)
        ocr_res = OCRService.extract_text(processed_pages)
        raw_text = ocr_res["extracted_text"]
        
        # 5. Document Classifier
        document_type = ClassificationService.classify(raw_text)
        
        # 6. Field Parser (regex)
        extract_res = FieldExtractionService.extract_fields(document_type, raw_text)
        extracted_fields = extract_res["extracted_fields"]
        
        # Parse profile data if available
        import json
        profile_dict = None
        if profile_data:
            try:
                profile_dict = json.loads(profile_data)
            except Exception:
                pass
        
        # 7. Verification Rules
        verify_res = VerificationService.verify(document_type, extracted_fields, profile_dict)
        
        # 8. Cross Validation (MRZ match and mock DB lookup)
        cross_res = CrossValidationService.cross_validate(document_type, extracted_fields)
        
        # 9. Fraud Detection (OpenCV image quality metrics)
        # Use the normalized image (always a PNG) instead of raw upload (which could be a PDF)
        # Pass doc_type so face detection is skipped for non-photo documents (PAN, Aadhaar)
        fraud_image_path = normalized_image_path or os.path.abspath(file_path)
        fraud_res = FraudDetectionService.detect(fraud_image_path, doc_type=document_type)
        
        # 10. Merge Cross-Validation results into Verification results for Decision
        passed_verify = list(verify_res.get("passed_checks") or [])
        failed_verify = list(verify_res.get("failed_checks") or [])
        
        for check_name, check_data in cross_res.items():
            if check_data["passed"]:
                passed_verify.append(check_name)
            else:
                failed_verify.append(check_name)
                
        verify_res["passed_checks"] = passed_verify
        verify_res["failed_checks"] = failed_verify
        if failed_verify:
            verify_res["verified"] = False
            verify_res["overall_valid"] = False
            
        # 11. Decision Aggregation
        decision_res = DecisionService.decide(verify_res, fraud_res)
        
        return PipelineResponse(
            request_id=upload_res["request_id"],
            filename=filename,
            original_filename=upload_res["original_filename"],
            document_type=document_type,
            raw_text=raw_text,
            extracted_fields=extracted_fields,
            verification_result=verify_res,
            cross_validation_result=cross_res,
            fraud_result=fraud_res,
            decision_result=decision_res,
            normalized_image_path=normalized_image_path,
            preprocessed_image_path=preprocessed_image_path,
            status="SUCCESS",
            message="Verification pipeline executed successfully"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"message": f"Pipeline error: {str(e)}", "status": "ERROR"}
        )


# =========================================
# HEALTH ROUTE
# =========================================

@router.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


# =========================================
# UPLOAD ROUTE
# =========================================

@router.post(
    "/upload",
    response_model=UploadResponse
)
async def upload_document(
    file: UploadFile = File(...)
):
    response = (
        await IngestionService
        .process_upload(file)
    )
    return UploadResponse(**response)


# =========================================
# NORMALIZATION ROUTE
# =========================================

@router.post(
    "/normalize",
    response_model=NormalizationResponse
)
async def normalize_document(
    file_path: str
):
    response = (
        NormalizationService
        .normalize_document(file_path)
    )
    return NormalizationResponse(**response)


# =========================================
# PREPROCESSING ROUTE
# =========================================

@router.post(
    "/preprocess",
    response_model=PreprocessingResponse
)
async def preprocess_document(
    request: PreprocessingRequest = Body(...)
):
    response = (
        PreprocessingService
        .preprocess_document(
            request.normalized_pages
        )
    )
    return PreprocessingResponse(
        **response
    )


# =========================================
# OCR ROUTE
# =========================================

@router.post(
    "/ocr",
    response_model=OCRResponse
)
async def extract_ocr(
    request: OCRRequest = Body(...)
):
    response = (
        OCRService
        .extract_text(
            request.processed_pages
        )
    )
    return OCRResponse(
        **response
    )


# =========================================
# FIELD EXTRACTION ROUTE
# =========================================

@router.post(
    "/extract-fields",
    response_model=FieldExtractionResponse
)
async def extract_fields(
    request: FieldExtractionRequest = Body(...)
):
    response = (
        FieldExtractionService
        .extract_fields(
            request.document_type,
            request.extracted_text
        )
    )
    return FieldExtractionResponse(
        **response
    )


# =========================================
# VERIFICATION ROUTE
# =========================================

@router.post(
    "/verify",
    response_model=VerificationResponse
)
async def verify_document(
    request: VerificationRequest = Body(...)
):
    response = (
        VerificationService
        .verify(
            request.document_type,
            request.extracted_fields
        )
    )
    return VerificationResponse(
        **response
    )


# =========================================
# FRAUD DETECTION ROUTE
# =========================================

@router.post(
    "/fraud-detect",
    response_model=FraudDetectionResponse
)
async def detect_fraud(
    request: FraudDetectionRequest = Body(...)
):
    response = (
        FraudDetectionService
        .detect(
            request.image_path
        )
    )
    return FraudDetectionResponse(
        **response
    )


# =========================================
# DECISION ROUTE
# =========================================

@router.post(
    "/decision",
    response_model=DecisionResponse
)
async def make_decision(
    request: DecisionRequest = Body(...)
):
    response = (
        DecisionService
        .decide(
            request.verification_result,
            request.fraud_result
        )
    )
    return DecisionResponse(
        **response
    )