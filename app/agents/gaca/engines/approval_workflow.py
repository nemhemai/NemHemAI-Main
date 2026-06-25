"""4.8 Approval Workflow Governance Engine - tracks approval and escalation workflows.

Supports multi-level approvals, escalations, delegations, department/supervisor reviews.
Captures: reviewer, approver, escalation path, approval timestamp, decision rationale.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Approval


def record_approval(db: Session, application_id: str, reviewer: str | None = None,
                    approver: str | None = None, escalation_path: list | None = None,
                    decision_rationale: str | None = None) -> Approval:
    row = Approval(
        application_id=application_id,
        reviewer=reviewer,
        approver=approver,
        escalation_path=escalation_path,
        decision_rationale=decision_rationale,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def workflow_for(db: Session, application_id: str) -> list[Approval]:
    return db.execute(
        select(Approval).where(Approval.application_id == application_id)
        .order_by(Approval.approval_timestamp.asc())
    ).scalars().all()
