from pydantic import BaseModel


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
# NORMALIZATION RESPONSE
# =========================================

class NormalizedPage(BaseModel):

    page_number: int

    normalized_path: str


class NormalizationResponse(BaseModel):

    request_id: str

    document_type: str

    total_pages: int

    normalized_pages: list[NormalizedPage]

    status: str
    
# =========================================
# PREPROCESSING RESPONSE
# =========================================

class ProcessedPage(BaseModel):

    page_number: int

    processed_path: str


class PreprocessingResponse(BaseModel):

    request_id: str

    total_pages: int

    processed_pages: list[ProcessedPage]

    status: str
    
# =========================================
# PREPROCESSING REQUEST
# =========================================

class PreprocessingRequest(BaseModel):

    normalized_pages: list
    
# =========================================
# OCR RESPONSE
# =========================================

class OCRLine(BaseModel):

    text: str

    confidence: float


class OCRResponse(BaseModel):

    request_id: str

    total_pages: int

    extracted_text: str

    ocr_lines: list[OCRLine]

    status: str
    
# =========================================
# OCR REQUEST
# =========================================

class OCRRequest(BaseModel):

    processed_pages: list