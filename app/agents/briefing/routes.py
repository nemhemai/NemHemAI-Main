from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.briefing.service import BriefingAgent, rate_briefing, OLLAMA_MODEL

router = APIRouter()

class BriefingRequest(BaseModel):
    query: str
    context_texts: list[str] = []
    role: str = "default"
    model: str = OLLAMA_MODEL

class RatingRequest(BaseModel):
    json_path: str
    rating: int

@router.post("/generate")
def generate_briefing(req: BriefingRequest):
    result = BriefingAgent(model=req.model).run(
        query=req.query, docs_path="", context_texts=req.context_texts, role=req.role
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Briefing generation failed"))
    return result

@router.post("/rate")
def rate_briefing_api(req: RatingRequest):
    result = rate_briefing(req.json_path, req.rating)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Rating failed"))
    return result
