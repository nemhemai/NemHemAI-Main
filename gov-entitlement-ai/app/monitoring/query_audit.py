# app/monitoring/query_audit.py

"""
Query Audit Logger

Purpose:
--------------------------------------------------
Logs every query execution in the RAG system.

Design Principles:
--------------------------------------------------
- Non-blocking (must NOT break query flow)
- Safe (failures in logging should not crash system)
- Consistent with ingestion audit design
- Stores full trace: user → query → retrieval → response

Usage:
--------------------------------------------------
log_query_event({...})
"""

import logging
from typing import Any, Dict
import json

from app.core.database import get_db_conn, release_db_conn

print("LOGGING QUERY AUDIT...")

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# MAIN LOGGER FUNCTION
# ──────────────────────────────────────────────────────────────

def log_query_event(event: Dict[str, Any]) -> None:
    """
    Insert query audit log into database.

    Expected keys in event:
    --------------------------------------------------
    user_id
    username
    query
    response
    chunks (list)
    documents (list)
    confidence
    latency
    llm_model
    status
    error (optional)
    """

    conn = None

    try:
        conn = get_db_conn()

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO query_audit_logs (
                    user_id,
                    username,
                    query_text,
                    response_text,
                    retrieved_chunk_ids,
                    retrieved_document_ids,
                    confidence,
                    latency_ms,
                    llm_model,
                    status,
                    error_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event.get("user_id"),
                    event.get("username"),
                    event.get("query"),
                    event.get("response"),
                    json.dumps(event.get("chunks") or []),
                    json.dumps(event.get("documents") or []),
                    event.get("confidence"),
                    event.get("latency"),
                    event.get("llm_model"),
                    event.get("status"),
                    event.get("error"),
                )
            )

        conn.commit()

    except Exception as e:
        # 🔥 DO NOT BREAK MAIN FLOW
        logger.error(f"Query audit logging failed: {e}")

    finally:
        if conn:
            release_db_conn(conn)