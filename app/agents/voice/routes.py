from fastapi import APIRouter, Request, HTTPException
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/haptik-webhook")
async def haptik_webhook(request: Request):
    """
    Webhook endpoint for Haptik or Yellow.ai to push STT text 
    or request backend routing.
    """
    # 1. Validate Webhook Secret
    # 2. Extract Intent and Entities
    # 3. Route to Grievance or Entitlement API
    
    payload = await request.json()
    logger.info(f"Received Voice Webhook payload: {payload}")
    
    intent = payload.get("intent", "UNKNOWN")
    
    if intent == "CHECK_GRIEVANCE_STATUS":
        # TODO: Call Grievance API
        return {"status": "success", "response": "Your grievance is currently OPEN."}
    elif intent == "CHECK_ENTITLEMENT":
        # TODO: Call Entitlement API (Currently a stub)
        return {"status": "success", "response": "Entitlement check is currently unavailable."}
    
    return {"status": "error", "message": "Unhandled intent"}
