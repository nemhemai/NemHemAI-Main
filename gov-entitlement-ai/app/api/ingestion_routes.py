# app/api/ingestion_routes.py

from importlib.metadata import metadata
from typing import List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
import uuid
import os

from app.core.database import get_db_conn, release_db_conn
from app.ingestion_orchestrator.pipeline_executor import start_pipeline_async
from app.authentication.dependencies import get_current_user
from app.monitoring.ingestion_audit import log_ingestion_event

router = APIRouter()


# ===============================================================
# 🔍 SINGLE DOCUMENT UPLOAD
# ===============================================================
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),

    # 🔐 AUTH (from JWT)
    user: dict = Depends(get_current_user),
    

    # REQUIRED (strict schema)
    title: str = Form(...),
    issuing_authority: str = Form(...),
    jurisdiction: str = Form(...),
    document_type: str = Form(...),
    primary_language: str = Form(...),

    # OPTIONAL
    document_number: str = Form(None),
    department_code: str = Form(None),
    state_origin: str = Form(None),
    security_level: str = Form("public"),

    version_label: str = Form(None),
    publication_date: str = Form(None),
    effective_date: str = Form(None),
):
    """
    Upload single document and trigger ingestion pipeline.

    🔐 Includes:
    - user tracking
    - audit logging
    - metadata enrichment
    """
    
    print("USER:", user)

    try:
        job_id = str(uuid.uuid4())

        # -------------------------------
        # FILE VALIDATION
        # -------------------------------
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        os.makedirs("storage", exist_ok=True)
        file_path = os.path.join("storage", file.filename)

        with open(file_path, "wb") as f:
            f.write(await file.read())

        # -------------------------------
        # STRICT VALIDATION (DB aligned)
        # -------------------------------
        if jurisdiction not in ["central", "state", "municipal"]:
            raise HTTPException(status_code=400, detail="Invalid jurisdiction")

        if document_type not in [
            "act", "rule", "policy", "circular",
            "notification", "report", "guideline",
            "charter", "manual", "budget", "announcement"
        ]:
            raise HTTPException(status_code=400, detail="Invalid document_type")

        if security_level not in ["public", "internal", "confidential"]:
            raise HTTPException(status_code=400, detail="Invalid security_level")

        # -------------------------------
        # METADATA (ENRICHED WITH USER + JOB)
        # -------------------------------
        metadata = {
            "title": title,
            "document_number": document_number,
            "issuing_authority": issuing_authority,
            "department_code": department_code,
            "jurisdiction": jurisdiction,
            "document_type": document_type,
            "primary_language": primary_language,
            "state_origin": state_origin,
            "security_level": security_level,
            "version_label": version_label,
            "publication_date": publication_date,
            "effective_date": effective_date,

            # 🔐 USER CONTEXT
            "user_id": user["user_id"],
            "uploaded_by": user["username"],

            # 🔗 JOB CONTEXT (CRITICAL FOR AUDIT)
            "job_id": job_id,
        }

        # Remove nulls
        metadata = {k: v for k, v in metadata.items() if v is not None}

        # -------------------------------
        # JOB TRACKING (DB)
        # -------------------------------
        conn = get_db_conn()

        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ingestion_jobs (job_id, file_name, status)
                VALUES (%s, %s, %s)
            """, (job_id, os.path.basename(file.filename), "UPLOADED"))

        conn.commit()
        release_db_conn(conn)

        # -------------------------------
        # ✅ AUDIT LOG (UPLOAD SUCCESS)
        # -------------------------------
        log_ingestion_event({
            "job_id": str(job_id),
            "user_id": str(user["user_id"]),
            "username": user.get("username"),
            "action": "upload",
            "stage": "UPLOADED",
            "status": "success",
            "message": f"{file.filename} uploaded"
        })

        # -------------------------------
        # PIPELINE (UNCHANGED)
        # -------------------------------
        start_pipeline_async(job_id, file_path, metadata)

        return {
            "job_id": job_id,
            "message": "Processing started"
        }

    # -------------------------------
    # ❌ FAILURE AUDIT
    # -------------------------------
    except Exception as e:

        log_ingestion_event({
            "job_id": None,
            "user_id": str(user["user_id"]) if user else None,
            "username": user.get("username") if user else None,
            "action": "upload",
            "stage": "UPLOADED",
            "status": "failed",
            "message": str(e),
            "error_code": "UPLOAD_ERROR"
        })

        raise


# ===============================================================
# 📊 JOB STATUS
# ===============================================================
@router.get("/status/{job_id}")
def get_status(job_id: str):
    conn = get_db_conn()


    try:
        with conn.cursor() as cur:
            # Auto-fail jobs that are older than 15 minutes and still in active state
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'FAILED',
                    error = 'Job timed out or server restarted',
                    updated_at = NOW()
                WHERE job_id = %s
                  AND status IN ('UPLOADED', 'REGISTERED', 'EXTRACTING', 'VALIDATING', 'STORING_ELEMENTS', 'CHUNKING', 'EMBEDDING')
                  AND created_at < NOW() - INTERVAL '15 minutes'
            """, (job_id,))
            conn.commit()

            cur.execute("""
                SELECT status, progress, error
                FROM ingestion_jobs
                WHERE job_id = %s
            """, (job_id,))

            row = cur.fetchone()

        if not row:
            return {
                "status": "FAILED",
                "progress": 0,
                "error": "Job not found"
            }

        return {
            "status": row[0],
            "progress": row[1],
            "error": row[2]
        }

    finally:
        release_db_conn(conn)


# ===============================================================
# 📦 BULK UPLOAD
# ===============================================================
@router.post("/bulk-upload")
async def bulk_upload(
    files: List[UploadFile] = File(...),
    metadata_files: List[UploadFile] = File(...),

    user = Depends(get_current_user),
):

    import json

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No PDF files provided")

    if len(metadata_files) == 0:
        raise HTTPException(status_code=400, detail="No metadata files provided")

    metadata_map = {}

    for meta_file in metadata_files:
        if not meta_file.filename.lower().endswith(".json"):
            continue

        content = await meta_file.read()

        try:
            metadata_json = json.loads(content.decode("utf-8"))
        except:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON: {meta_file.filename}"
            )

        base_name, _ = os.path.splitext(meta_file.filename)
        metadata_map[base_name] = metadata_json

    job_ids = []
    conn = get_db_conn()

    try:
        for file in files:

            if not file.filename.lower().endswith(".pdf"):
                continue

            base_name, _ = os.path.splitext(file.filename)

            if base_name not in metadata_map:
                continue

            job_id = str(uuid.uuid4())

            os.makedirs("storage", exist_ok=True)
            safe_filename = os.path.basename(file.filename)
            file_path = os.path.join("storage", safe_filename)

            with open(file_path, "wb") as f:
                f.write(await file.read())

            metadata = metadata_map[base_name]

            # 🔐 USER + JOB CONTEXT
            metadata["user_id"] = user["user_id"]
            metadata["uploaded_by"] = user.get("username")
            metadata["job_id"] = job_id

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ingestion_jobs (job_id, file_name, status)
                    VALUES (%s, %s, %s)
                """, (job_id, os.path.basename(file.filename), "UPLOADED"))

            # ✅ BULK AUDIT LOG
            log_ingestion_event({
                "job_id": str(job_id),
                "user_id": str(user["user_id"]),
                "username": user.get("username"),
                "action": "upload",
                "stage": "UPLOADED",
                "status": "success",
                "message": f"{file.filename} uploaded (bulk)"
            })

            job_ids.append({
                "job_id": job_id,
                "file_name": file.filename
            })

            start_pipeline_async(job_id, file_path, metadata)

        conn.commit()

    finally:
        release_db_conn(conn)

    return {
        "message": "Bulk ingestion started",
        "jobs": job_ids
    }


# ===============================================================
# 📊 BULK STATUS CHECK / RESUME
# ===============================================================
class BulkStatusRequest(BaseModel):
    filenames: List[str]

@router.post("/bulk-status")
def get_bulk_status(request: BulkStatusRequest, user=Depends(get_current_user)):
    """
    Check the current ingestion status of multiple files from the DB.
    Returns status, progress, job_id, and error for each file.
    """
    conn = get_db_conn()

    results = {}
    try:
        with conn.cursor() as cur:
            # Auto-fail all active jobs that are older than 15 minutes
            cur.execute("""
                UPDATE ingestion_jobs
                SET status = 'FAILED',
                    error = 'Job timed out or server restarted',
                    updated_at = NOW()
                WHERE status IN ('UPLOADED', 'REGISTERED', 'EXTRACTING', 'VALIDATING', 'STORING_ELEMENTS', 'CHUNKING', 'EMBEDDING')
                  AND created_at < NOW() - INTERVAL '15 minutes'
            """)
            conn.commit()

            for filename in request.filenames:
                basename = os.path.basename(filename)
                
                # 1st Check: Look for an active job created within the last 15 minutes
                cur.execute("""
                    SELECT status, progress, job_id, error
                    FROM ingestion_jobs
                    WHERE file_name = %s
                      AND status IN ('UPLOADED', 'REGISTERED', 'EXTRACTING', 'VALIDATING', 'STORING_ELEMENTS', 'CHUNKING', 'EMBEDDING')
                      AND created_at > NOW() - INTERVAL '15 minutes'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (basename,))
                active_job = cur.fetchone()
                
                if active_job:
                    results[filename] = {
                        "status": active_job[0],
                        "progress": active_job[1],
                        "job_id": str(active_job[2]) if active_job[2] else None,
                        "error": active_job[3] or ""
                    }
                else:
                    # 2nd Check: Look up in documents registry and verify BOTH chunks and embeddings exist
                    cur.execute("""
                        SELECT d.document_id
                        FROM documents d
                        JOIN document_chunks c ON d.document_id = c.document_id
                        JOIN document_embeddings e ON d.document_id = e.document_id
                        WHERE d.file_name = %s
                        LIMIT 1
                    """, (basename,))
                    doc_row = cur.fetchone()
                    
                    if doc_row:
                        results[filename] = {
                            "status": "COMPLETED",
                            "progress": 100,
                            "job_id": None,
                            "error": ""
                        }
                    else:
                        # 3rd Check: Fallback to the most recent job overall (e.g. if it failed or completed)
                        cur.execute("""
                            SELECT status, progress, job_id, error
                            FROM ingestion_jobs
                            WHERE file_name = %s
                            ORDER BY created_at DESC
                            LIMIT 1
                        """, (basename,))
                        last_job = cur.fetchone()
                        
                        if last_job:
                            results[filename] = {
                                "status": last_job[0],
                                "progress": last_job[1],
                                "job_id": str(last_job[2]) if last_job[2] else None,
                                "error": last_job[3] or ""
                            }
                        else:
                            results[filename] = {
                                "status": "READY",
                                "progress": 0,
                                "job_id": None,
                                "error": ""
                            }
        return {"statuses": results}
    finally:
        release_db_conn(conn)