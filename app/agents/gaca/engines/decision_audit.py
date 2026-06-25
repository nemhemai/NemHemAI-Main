"""4.1 Decision Audit Engine - captures and records all platform decisions.

Outputs: Decision History, Audit Records, Audit Reports.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Decision


def record_decision(db: Session, **fields) -> Decision:
    """Records a decision with the spec's stored attributes."""
    row = Decision(
        decision_id=fields["decision_id"],
        citizen_id=fields.get("citizen_id"),
        application_id=fields.get("application_id"),
        scheme_id=fields.get("scheme_id"),
        decision_type=fields.get("decision_type"),
        decision_result=fields.get("decision_result"),
        responsible_agent=fields.get("responsible_agent"),
        confidence_score=fields.get("confidence_score"),
        policy_id=fields.get("policy_id"),
        profile_snapshot=fields.get("profile_snapshot"),
        retrieved_context=fields.get("retrieved_context"),
    )
    db.merge(row)
    db.commit()
    return db.get(Decision, fields["decision_id"])


def decision_history(db: Session, citizen_id: str) -> list[Decision]:
    return db.execute(
        select(Decision).where(Decision.citizen_id == citizen_id)
        .order_by(Decision.timestamp.desc())
    ).scalars().all()


def audit_records(db: Session, application_id: str) -> list[Decision]:
    return db.execute(
        select(Decision).where(Decision.application_id == application_id)
    ).scalars().all()
