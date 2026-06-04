# app/api/ingestion_routes.py

from importlib.metadata import metadata
from typing import List

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

        # Allowed any document type for flexibility

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

            #  USER CONTEXT
            "user_id": user["user_id"],
            "uploaded_by": user["username"],

            #  JOB CONTEXT (CRITICAL FOR AUDIT)
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
            """, (job_id, file.filename, "UPLOADED"))

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
    # FAILURE AUDIT
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

        import re
        base_name = re.sub(r'(?i)\.json$', '', meta_file.filename)
        metadata_map[base_name] = metadata_json

    job_ids = []
    conn = get_db_conn()

    try:
        for file in files:

            if not file.filename.lower().endswith(".pdf"):
                continue

            # Do case-insensitive replace for base_name
            import re
            base_name = re.sub(r'(?i)\.pdf$', '', file.filename)

            if base_name not in metadata_map:
                continue

            # -----------------------------------------------
            # DUPLICATE CHECK: skip if already in pipeline
            # -----------------------------------------------
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT job_id, status FROM ingestion_jobs
                    WHERE file_name = %s
                    ORDER BY created_at DESC LIMIT 1
                """, (file.filename,))
                existing = cur.fetchone()

            if existing:
                existing_job_id, existing_status = existing
                if existing_status in ("COMPLETED", "EXTRACTING", "EMBEDDING"):
                    # Already done or actively running — skip
                    job_ids.append({
                        "job_id": existing_job_id,
                        "file_name": file.filename,
                        "skipped": True,
                        "existing_status": existing_status
                    })
                    continue
                elif existing_status == "UPLOADED":
                    # Job exists but pipeline lost its thread (e.g. server restart)
                    # Re-trigger pipeline without creating a new job
                    existing_meta = metadata_map[base_name]
                    existing_meta["user_id"] = user["user_id"]
                    existing_meta["uploaded_by"] = user.get("username")
                    existing_meta["job_id"] = existing_job_id
                    existing_file_path = os.path.join("storage", os.path.basename(file.filename))
                    if not os.path.exists(existing_file_path):
                        # File not on disk yet — save it
                        content = await file.read()
                        with open(existing_file_path, "wb") as fout:
                            fout.write(content)
                    start_pipeline_async(existing_job_id, existing_file_path, existing_meta)
                    job_ids.append({
                        "job_id": existing_job_id,
                        "file_name": file.filename,
                        "resumed": True
                    })
                    continue

            job_id = str(uuid.uuid4())

            os.makedirs("storage", exist_ok=True)
            safe_filename = os.path.basename(file.filename)
            file_path = os.path.join("storage", safe_filename)

            with open(file_path, "wb") as f:
                f.write(await file.read())

            metadata = metadata_map[base_name]

            # 🔥 FIX: Force type to lowercase to avoid violating the DB check constraint (e.g. "Act" -> "act")
            if "type" in metadata and isinstance(metadata["type"], str):
                metadata["type"] = metadata["type"].lower()
            if "document_type" in metadata and isinstance(metadata["document_type"], str):
                metadata["document_type"] = metadata["document_type"].lower()

            # 🔐 USER + JOB CONTEXT
            metadata["user_id"] = user["user_id"]
            metadata["uploaded_by"] = user.get("username")
            metadata["job_id"] = job_id

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ingestion_jobs (job_id, file_name, status)
                    VALUES (%s, %s, %s)
                """, (job_id, file.filename, "UPLOADED"))

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

    if not job_ids:
        raise HTTPException(status_code=400, detail="No files were successfully matched and processed. Please ensure PDF and JSON filenames match exactly.")

    return {
        "message": "Bulk ingestion started",
        "jobs": job_ids
    }