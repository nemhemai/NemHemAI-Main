# app/api/entitlement_routes.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import json

from app.core.database import get_db_conn, release_db_conn
from app.authentication.dependencies import get_current_user
from app.agents.entitlement.services.entitlement_service import run_entitlement_check

router = APIRouter()

# ─────────────────────────────────────────────────────────────
# 📦 REQUEST SCHEMA
# ─────────────────────────────────────────────────────────────

class EntitlementRequest(BaseModel):
    citizen_id: str | None = None
    raw_query: str
    verified_documents: list[str] = []

# ─────────────────────────────────────────────────────────────
# 🔍 ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/v1/entitlement")
def initiate_entitlement_check(
    request: EntitlementRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a citizen query for entitlement processing.
    """
    user = None
    raw_query = request.raw_query.strip()
    citizen_id = request.citizen_id.strip() if request.citizen_id else None
    user_id = user.get("user_id") if user else None

    if not raw_query:
        raise HTTPException(
            status_code=400,
            detail="Query text cannot be empty"
        )

    conn = get_db_conn()
    try:
        query_id = str(uuid.uuid4())
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entitlement_queries (
                    query_id,
                    user_id,
                    citizen_id,
                    raw_query,
                    status
                )
                VALUES (%s, %s, %s, %s, 'PENDING')
            """, (query_id, user_id, citizen_id, raw_query))
            conn.commit()

        # Add check to background tasks to execute asynchronously
        background_tasks.add_task(
            run_entitlement_check,
            query_id=query_id,
            raw_query=raw_query,
            user_id=user_id,
            verified_docs=request.verified_documents
        )

        return {
            "query_id": query_id,
            "status": "PROCESSING",
            "message": "Entitlement check successfully queued."
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        release_db_conn(conn)


@router.get("/v1/entitlement/{query_id}")
def get_entitlement_status(
    query_id: str
):
    """
    Retrieve the status and results of an entitlement check.
    """
    user = None
    try:
        # Validate UUID format
        uuid.UUID(query_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid query_id format.")

    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    query_id, 
                    user_id, 
                    citizen_id, 
                    raw_query, 
                    extracted_profile, 
                    scheme_matches, 
                    determination, 
                    status, 
                    error_message, 
                    created_at, 
                    updated_at
                FROM entitlement_queries
                WHERE query_id = %s
            """, (query_id,))
            row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Entitlement query not found"
            )

        (
            q_id, u_id, c_id, raw_q, ext_profile, matches, det, status, err, created, updated
        ) = row

        return {
            "query_id": str(q_id),
            "user_id": str(u_id) if u_id else None,
            "citizen_id": c_id,
            "raw_query": raw_q,
            "extracted_profile": ext_profile if ext_profile else {},
            "scheme_matches": matches if matches else [],
            "determination": det if det else {},
            "status": status,
            "error_message": err,
            "created_at": created.isoformat() if created else None,
            "updated_at": updated.isoformat() if updated else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        release_db_conn(conn)


@router.post("/v1/applications/submit")
def submit_application(request: dict):
    """
    Submit an application for a specific scheme.
    """
    import uuid
    tracking_id = f"APP-{str(uuid.uuid4())[:8].upper()}"
    return {
        "status": "SUCCESS",
        "tracking_id": tracking_id,
        "message": "Application submitted successfully."
    }

