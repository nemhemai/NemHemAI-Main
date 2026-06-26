# app/api/query_routes.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.query_service import run_query, run_query_stream
from app.authentication.dependencies import get_current_user

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# 📦 REQUEST SCHEMA
# ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str


# ─────────────────────────────────────────────────────────────
# 🔍 QUERY ENDPOINT
# ─────────────────────────────────────────────────────────────

@router.post("/query")
def query_documents(request: QueryRequest, user=Depends(get_current_user)):
    
    query = request.query
    
    """
    Execute query against ingested documents.

    Input:
        { "query": "..." }

    Output:
        {
          "query": "...",
          "answer_original": "...",
          "answer_translated": "...",
          "citations": [...],
          "confidence": "high"
        }
    """

    query = request.query

    # 🔒 Basic validation
    if not query or not query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty"
        )

    try:
        result = run_query(query, user)
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/query/stream")
def query_documents_stream(request: QueryRequest, user=Depends(get_current_user)):
    """
    Streaming Query endpoint using Server-Sent Events (SSE).
    Yields citations first, then stream tokens as they are generated.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return StreamingResponse(run_query_stream(query, user), media_type="text/event-stream")