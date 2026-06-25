"""4.13 Appeals & Reconsideration Engine - supports citizen appeals.

Workflow: Decision -> Appeal Submission -> Review -> Reconsideration -> Final Decision.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Appeal

STAGES = ["submission", "review", "reconsideration", "final"]


def submit_appeal(db: Session, decision_id: str, grounds: str | None = None) -> Appeal:
    row = Appeal(
        decision_id=decision_id,
        status="submission",
        history=[{"stage": "submission", "at": datetime.now(timezone.utc).isoformat(),
                  "grounds": grounds}],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def advance_appeal(db: Session, appeal_id: int, note: str | None = None,
                   final_decision: str | None = None) -> Appeal:
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise ValueError("appeal not found")
    idx = STAGES.index(appeal.status)
    if idx < len(STAGES) - 1:
        appeal.status = STAGES[idx + 1]
    history = list(appeal.history or [])
    history.append({"stage": appeal.status,
                    "at": datetime.now(timezone.utc).isoformat(), "note": note})
    appeal.history = history
    if appeal.status == "final" and final_decision:
        appeal.final_decision = final_decision
    db.commit()
    db.refresh(appeal)
    return appeal
