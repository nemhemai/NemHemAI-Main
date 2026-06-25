"""4.5 User Activity Audit Engine - tracks activities of citizens, officers,
administrators, and AI agents.

Each event gets an integrity hash so the governance record is immutable
(Section 5, Stage 7: "Immutable governance records are created").
"""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent


def _hash(actor_type, actor_id, action, target, details) -> str:
    canonical = json.dumps(
        {"actor_type": actor_type, "actor_id": actor_id, "action": action,
         "target": target, "details": details},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def log_activity(db: Session, actor_type: str, action: str,
                 actor_id: str | None = None, target: str | None = None,
                 details: dict | None = None) -> AuditEvent:
    row = AuditEvent(
        actor_type=actor_type, actor_id=actor_id, action=action,
        target=target, details=details,
        integrity_hash=_hash(actor_type, actor_id, action, target, details),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def activity_log(db: Session, actor_type: str | None = None,
                 actor_id: str | None = None) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if actor_type:
        stmt = stmt.where(AuditEvent.actor_type == actor_type)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    return db.execute(stmt).scalars().all()
