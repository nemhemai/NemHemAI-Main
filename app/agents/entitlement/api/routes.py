# app/api/entitlement_routes.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import json

from app.core.database import get_db_conn, release_db_conn
from app.authentication.dependencies import get_current_user
from app.agents.entitlement.services.entitlement_service import run_entitlement_check
from app.services.audit_service import log_entitlement_audit

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
    
    citizen_id = request.get("citizen_id", "UNKNOWN")
    scheme_name = request.get("scheme_id", "UNKNOWN_SCHEME")
    documents = request.get("documents", [])
    
    # Log the submission to the audit trail
    log_entitlement_audit(
        citizen_id=citizen_id,
        query_id=tracking_id,
        scheme_name=scheme_name,
        action="APPLICATION_SUBMITTED",
        decision_trace={
            "verdict": "SUBMITTED",
            "message": "Application submitted successfully.",
            "tracking_id": tracking_id,
            "documents_attached": documents
        }
    )
    
    # ------------------------------------------------------------------
    # TRIGGER GACA FOR SUBMISSION
    # ------------------------------------------------------------------
    try:
        from app.agents.gaca.database import get_db
        from app.agents.gaca.schemas import GovernanceEventIn, AIMetadataIn
        from app.agents.gaca.workflow import process_event
        db_gen = get_db()
        db_session = next(db_gen)
        try:
            event = GovernanceEventIn(
                event_type="application_submission",
                responsible_agent="entitlement",
                citizen_id=str(citizen_id),
                decision_id=f"SUBMIT_{tracking_id}",
                application_id=tracking_id,
                scheme_id=scheme_name,
                decision_type="submission",
                decision_result="APPLICATION_SUBMITTED",
                confidence_score=1.0,
                policy_id=scheme_name,
                profile_snapshot={},
                retrieved_context={
                    "documents_attached": documents,
                    "message": "Application submitted successfully."
                },
                required_documents=[],
                ai_metadata=AIMetadataIn(
                    llm="none",
                    generated_response="System event.",
                    confidence_score=1.0
                )
            )
            process_event(db_session, event)
        finally:
            db_session.close()
    except Exception as e:
        import logging
        logging.error("Failed to push submission event to GACA: %s", e)

    return {
        "status": "SUCCESS",
        "tracking_id": tracking_id,
        "message": "Application submitted successfully."
    }

