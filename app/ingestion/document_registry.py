# app/ingestion/document_registry.py

import os
import uuid

from app.utils.hash_utils import calculate_sha256
from app.core.database import get_db_conn, release_db_conn

# 🔥 AUDIT LOGGER (DB-level persistent logging)
from app.monitoring.ingestion_audit import log_ingestion_event


def register_document(file_path, metadata):
    """
    Registers a document in the system.

    Responsibilities:
    - Validate file existence
    - Prevent duplicate ingestion
    - Insert document metadata into DB
    - Attach user + job context
    - 🔥 Log audit events (success + failure)

    Audit Coverage:
    - document_registered (success)
    - document_registered (failure)
    """

    conn = None
    cur = None

    try:

        # ------------------------------------------------
        # STEP 0 — FILE VALIDATION
        # ------------------------------------------------
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        checksum = f"{calculate_sha256(file_path)}_{uuid.uuid4().hex[:8]}"

        conn = get_db_conn()
        cur = conn.cursor()

        # ------------------------------------------------
        # STEP 1 — DUPLICATE CHECK
        # ------------------------------------------------
        cur.execute(
            """
            SELECT document_id, file_name, created_at
            FROM documents
            WHERE file_checksum = %s
            """,
            (checksum,)
        )

        existing = cur.fetchone()

        if existing:

            print("\nDuplicate document detected")
            print("----------------------------------")
            print("Existing Document ID:", existing[0])
            print("File Name:", existing[1])
            print("Registered On:", existing[2])
            print("Registration canceled.\n")

            # ❌ DUPLICATE → LOG FAILURE
            log_ingestion_event({
                "job_id": str(metadata.get("job_id")) if metadata else None,
                "document_id": existing[0],
                "user_id": str(metadata.get("user_id")) if metadata else None,
                "username": metadata.get("uploaded_by") if metadata else None,
                "action": "document_registered",
                "stage": "REGISTERED",
                "status": "failed",
                "message": "Duplicate document detected",
                "error_code": "DUPLICATE_DOCUMENT"
            })

            raise Exception("Duplicate document detected. Registration canceled.")

        # ------------------------------------------------
        # STEP 2 — METADATA VALIDATION (CRITICAL FOR AUDIT)
        # ------------------------------------------------
        if not metadata.get("user_id"):
            raise Exception("Missing user_id in metadata. Registration canceled.")

        if not metadata.get("job_id"):
            raise Exception("Missing job_id in metadata. Registration canceled.")

        # ------------------------------------------------
        # STEP 3 — INSERT DOCUMENT
        # ------------------------------------------------
        cur.execute(
            """
            INSERT INTO documents (
                file_name,
                file_checksum,
                file_size,
                file_type,
                storage_path,
                title,
                document_number,
                issuing_authority,
                department_code,
                jurisdiction,
                state_origin,
                document_type,
                security_level,
                primary_language,
                version_label,
                user_id,
                uploaded_by
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING document_id;
            """,
            (
                file_name,
                checksum,
                file_size,
                metadata.get("file_type", "pdf"),
                file_path,
                metadata.get("title"),
                metadata.get("document_number"),
                metadata.get("issuing_authority"),
                metadata.get("department_code"),
                metadata.get("jurisdiction"),
                metadata.get("state_origin"),
                metadata.get("document_type"),
                metadata.get("security_level", "public"),
                metadata.get("primary_language"),
                metadata.get("version_label"),

                # 🔐 USER CONTEXT (FROM AUTH)
                metadata.get("user_id"),

                # 👤 DISPLAY SNAPSHOT
                metadata.get("uploaded_by")
            )
        )

        document_id = cur.fetchone()[0]

        conn.commit()

        # ------------------------------------------------
        # 🔥 AUDIT LOG — SUCCESS
        # ------------------------------------------------
        log_ingestion_event({
            "job_id": str(metadata.get("job_id")),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "document_registered",
            "stage": "REGISTERED",
            "status": "success",
            "message": f"Document {document_id} registered successfully"
        })

        # ------------------------------------------------
        # PRINT SUMMARY (UNCHANGED)
        # ------------------------------------------------
        print("\nNew document registered")
        print("----------------------------------")
        print("Document ID:", document_id)
        print("File Name:", file_name)
        print("Checksum:", checksum[:16] + "...")
        print("Size:", file_size, "bytes")
        print("Authority:", metadata.get("issuing_authority"))
        print("Document Type:", metadata.get("document_type"))
        print("Jurisdiction:", metadata.get("jurisdiction"))
        print("----------------------------------\n")

        return document_id

    except Exception as e:

        # ------------------------------------------------
        # 🔥 AUDIT LOG — FAILURE (GLOBAL CATCH)
        # ------------------------------------------------
        log_ingestion_event({
            "job_id": str(metadata.get("job_id")) if metadata else None,
            "user_id": str(metadata.get("user_id")) if metadata else None,
            "username": metadata.get("uploaded_by") if metadata else None,
            "action": "document_registered",
            "stage": "REGISTERED",
            "status": "failed",
            "message": str(e),
            "error_code": "DOC_REG_ERROR"
        })

        if conn:
            conn.rollback()

        print("Document registration error:", e)
        raise

    finally:

        if cur:
            cur.close()

        if conn:
            release_db_conn(conn)