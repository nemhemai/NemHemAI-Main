# app/services/audit_service.py

from typing import Any
import json
from app.core.database import get_db_conn, release_db_conn

def log_entitlement_audit(
    citizen_id: str, 
    query_id: str, 
    scheme_name: str, 
    action: str, 
    decision_trace: dict[str, Any]
) -> None:
    """
    Step 14: Audit Agent.
    Logs decision traceability, eligibility justifications, and compliance records.
    Stores why a scheme was recommended/rejected, what rules were evaluated, and what documents were used.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO entitlement_audits (citizen_id, query_id, scheme_name, action, decision_trace)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                citizen_id, 
                query_id if query_id else None, 
                scheme_name, 
                action, 
                json.dumps(decision_trace)
            ))
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        # Fallback debug log, do not crash the primary pipeline
        print(f"Error logging audit record: {e}")
    finally:
        release_db_conn(conn)

def get_citizen_audit_logs(citizen_id: str) -> list[dict[str, Any]]:
    """
    Step 14: Audit Agent query.
    Retrieves the complete compliance logs and eligibility decision paths for a citizen.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT audit_id, query_id, scheme_name, action, decision_trace, created_at
                FROM entitlement_audits
                WHERE citizen_id = %s
                ORDER BY created_at DESC
            """, (citizen_id,))
            rows = cur.fetchall()
            
            logs = []
            for audit_id, q_id, scheme, action, trace, created in rows:
                trace_data = trace
                if isinstance(trace_data, str):
                    trace_data = json.loads(trace_data)
                logs.append({
                    "audit_id": str(audit_id),
                    "query_id": str(q_id) if q_id else None,
                    "scheme_name": scheme,
                    "action": action,
                    "decision_trace": trace_data,
                    "created_at": created.isoformat()
                })
            return logs
    finally:
        release_db_conn(conn)
