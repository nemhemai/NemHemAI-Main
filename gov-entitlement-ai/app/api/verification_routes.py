# app/api/verification_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.authentication.dependencies import get_current_user
from app.services.verification_service import run_document_verification, run_eligibility_reconfirmation

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 📦 SCHEMAS
# ─────────────────────────────────────────────────────────────

class DocumentVerifyRequest(BaseModel):
    citizen_id: str = Field(..., description="UUID of the citizen")
    document_type: str = Field(..., description="Aadhaar | Income Certificate | Caste/category certificate | Domicile Certificate | Disability Certificate")
    file_path: str = Field(..., description="Local path or URL of uploaded document")

class ReconfirmRequest(BaseModel):
    citizen_id: str = Field(..., description="UUID of the citizen")

# ─────────────────────────────────────────────────────────────
# 🔍 ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/verify-document")
def verify_document(
    request: DocumentVerifyRequest,
    user=Depends(get_current_user)
):
    """
    Step 7: Submit a document to the Verification Agent to run Classifier -> OCR -> Rules -> Cross Val -> Fraud checks.
    """
    try:
        result = run_document_verification(
            citizen_id=request.citizen_id,
            document_type=request.document_type,
            file_path=request.file_path
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reconfirm")
def reconfirm_eligibility(
    request: ReconfirmRequest,
    user=Depends(get_current_user)
):
    """
    Step 8: Consumer verification evidence and run final Eligibility Reconfirmation.
    """
    try:
        result = run_eligibility_reconfirmation(citizen_id=request.citizen_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
