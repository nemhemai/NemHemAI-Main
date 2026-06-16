# app/api/audit_routes.py

from fastapi import APIRouter, Depends, HTTPException

from app.authentication.dependencies import get_current_user
from app.services.audit_service import get_citizen_audit_logs

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 🔍 ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/logs/{citizen_id}")
def get_audit_logs(
    citizen_id: str,
    user=Depends(get_current_user)
):
    """
    Step 14: Query audit compliance records, decision justification, and rules checklist for administrative review.
    """
    try:
        return get_citizen_audit_logs(citizen_id=citizen_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
