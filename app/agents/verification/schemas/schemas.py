from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# =========================================
# ERROR RESPONSE
# =========================================

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    trace_id: str


# =========================================
# UPLOAD RESPONSE
# =========================================

class UploadResponse(BaseModel):
    request_id: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    status: str
    message: str


# =========================================
# NORMALIZATION
# =========================================

class NormalizedPage(BaseModel):
    page_number: int
    normalized_path: str


class NormalizationResponse(BaseModel):
    request_id: str
    document_type: str
    total_pages: int
    normalized_pages: List[NormalizedPage]
    status: str


# =========================================
# PREPROCESSING
# =========================================

class PreprocessingRequest(BaseModel):
    normalized_pages: List[Any]


class ProcessedPage(BaseModel):
    page_number: int
    processed_path: str


class PreprocessingResponse(BaseModel):
    request_id: str
    total_pages: int
    processed_pages: List[ProcessedPage]
    status: str


# =========================================
# OCR
# =========================================

class OCRRequest(BaseModel):
    processed_pages: List[Any]


class OCRLine(BaseModel):
    text: str
    confidence: float


class OCRResponse(BaseModel):
    request_id: str
    total_pages: int
    extracted_text: str
    ocr_lines: List[OCRLine]
    status: str


# =========================================
# FIELD EXTRACTION
# =========================================

class FieldExtractionRequest(BaseModel):
    document_type: str
    extracted_text: str


class FieldExtractionResponse(BaseModel):
    request_id: Optional[str] = None
    document_type: str
    extracted_fields: Dict[str, Any]
    status: str
    raw_text: Optional[str] = None
    success: Optional[bool] = None


# =========================================
# VERIFICATION
# =========================================

class VerificationRequest(BaseModel):
    document_type: str
    extracted_fields: Dict[str, Any]


class VerificationResponse(BaseModel):
    request_id: Optional[str] = None
    document_type: str
    verified: bool
    verification_details: Dict[str, Any]
    status: str
    passed_checks: Optional[List[str]] = None
    failed_checks: Optional[List[str]] = None
    success: Optional[bool] = None
    overall_valid: Optional[bool] = None
    confidence: Optional[float] = None
    checks: Optional[Dict[str, Any]] = None


# =========================================
# FRAUD DETECTION
# =========================================

class FraudDetectionRequest(BaseModel):
    image_path: str


class FraudDetectionResponse(BaseModel):
    request_id: Optional[str] = None
    fraud_risk: str
    fraud_score: float
    signals: Dict[str, Any]
    status: str
    fraud_flags: Optional[List[str]] = None
    face_detected: Optional[bool] = None
    success: Optional[bool] = None


# =========================================
# DECISION
# =========================================

class DecisionRequest(BaseModel):
    verification_result: Dict[str, Any]
    fraud_result: Dict[str, Any]
    doc_type: Optional[str] = None


class DecisionResponse(BaseModel):
    request_id: Optional[str] = None
    verified: bool
    confidence: float
    fraud_risk: str
    decision: str
    status: str
    reasons: Optional[List[str]] = None
    passed_checks: Optional[List[str]] = None
    failed_checks: Optional[List[str]] = None
    fraud_flags: Optional[List[str]] = None
    doc_type: Optional[str] = None
    success: Optional[bool] = None


# =========================================
# PIPELINE RESPONSE
# =========================================

class PipelineResponse(BaseModel):
    request_id: str
    filename: str
    original_filename: str
    document_type: str
    raw_text: str
    extracted_fields: Dict[str, Any]
    verification_result: Dict[str, Any]
    cross_validation_result: Dict[str, Any]
    fraud_result: Dict[str, Any]
    decision_result: Dict[str, Any]
    normalized_image_path: Optional[str] = None
    preprocessed_image_path: Optional[str] = None
    status: str
    message: str