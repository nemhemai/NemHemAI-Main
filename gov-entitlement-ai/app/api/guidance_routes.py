# app/api/guidance_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.authentication.dependencies import get_current_user
from app.services.guidance_service import (
    generate_guidance_data,
    submit_citizen_application,
    track_application_status
)

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 📦 SCHEMAS
# ─────────────────────────────────────────────────────────────

class SubmitApplicationRequest(BaseModel):
    citizen_id: str = Field(..., description="UUID of the citizen")
    scheme_name: str = Field(..., description="Name of the scheme")
    form_data: dict = Field(..., description="Completed application form values")
    submission_channel: str = Field("API", description="API | Portal | Officer Queue")

# ─────────────────────────────────────────────────────────────
# 🔍 ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/guide")
def get_guidance(
    citizen_id: str = Query(..., description="UUID of the citizen"),
    scheme_name: str = Query(..., description="Name of the scheme"),
    user=Depends(get_current_user)
):
    """
    Step 11: Get application form pre-filling assistance, affidavit text, and missing documents tracker.
    """
    try:
        return generate_guidance_data(citizen_id=citizen_id, scheme_name=scheme_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit")
def submit_application(
    request: SubmitApplicationRequest,
    user=Depends(get_current_user)
):
    """
    Step 12: Submit the completed application via API, Portal, or Officer Queue.
    """
    try:
        result = submit_citizen_application(
            citizen_id=request.citizen_id,
            scheme_name=request.scheme_name,
            form_data=request.form_data,
            submission_channel=request.submission_channel
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{application_id}/status")
def get_status(
    application_id: str,
    user=Depends(get_current_user)
):
    """
    Step 13: Track the live status, expected timeline, and regional officer remarks for a submitted application.
    """
    try:
        return track_application_status(application_id=application_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
