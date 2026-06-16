# app/api/citizen_routes.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from app.authentication.dependencies import get_current_user
from app.services.citizen_service import (
    register_citizen,
    get_citizen_profile,
    update_citizen_profile
)

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 📦 SCHEMAS
# ─────────────────────────────────────────────────────────────

class CitizenRegisterRequest(BaseModel):
    mobile_number: str = Field(..., description="10-digit mobile number")
    aadhaar_id: str = Field(..., description="12-digit Aadhaar number")
    email: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    personal_info: dict = Field(..., description="Name, address, state, urban/rural status")
    household_info: dict = Field(..., description="Family members, senior count, dependents, etc.")
    socio_economic_info: dict = Field(..., description="Income, occupation, land ownership, category")
    existing_benefits: Optional[list] = Field(None, description="List of currently active benefits")

# ─────────────────────────────────────────────────────────────
# 🔍 ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/register")
def register(
    request: CitizenRegisterRequest,
    user=Depends(get_current_user)
):
    """
    Step 1 & 2: Register citizen and run identity verification checks.
    """
    try:
        result = register_citizen(
            mobile_number=request.mobile_number,
            aadhaar_id=request.aadhaar_id,
            email=request.email
        )
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{citizen_id}/profile")
def get_profile(
    citizen_id: str,
    user=Depends(get_current_user)
):
    """
    Step 3: Retrieve the unified Citizen 360 profile.
    """
    try:
        return get_citizen_profile(citizen_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{citizen_id}/profile")
def update_profile(
    citizen_id: str,
    request: ProfileUpdateRequest,
    user=Depends(get_current_user)
):
    """
    Step 3 & 4: Update Citizen 360 profile and perform Household & Socio-Economic assessment.
    """
    try:
        return update_citizen_profile(
            citizen_id=citizen_id,
            personal_info=request.personal_info,
            household_info=request.household_info,
            socio_economic_info=request.socio_economic_info,
            existing_benefits=request.existing_benefits
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
