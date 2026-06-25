"""4.7 Human Override Governance Engine - tracks officer overrides of AI recommendations.

Captures: original AI recommendation, officer decision, override reason,
approval authority, supporting notes.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import HumanOverride


def record_override(db: Session, decision_id: str, original_ai_recommendation: str,
                    officer_decision: str, override_reason: str,
                    approval_authority: str | None = None,
                    supporting_notes: str | None = None) -> HumanOverride:
    row = HumanOverride(
        decision_id=decision_id,
        original_ai_recommendation=original_ai_recommendation,
        officer_decision=officer_decision,
        override_reason=override_reason,
        approval_authority=approval_authority,
        supporting_notes=supporting_notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def overrides_for(db: Session, decision_id: str) -> list[HumanOverride]:
    return db.execute(
        select(HumanOverride).where(HumanOverride.decision_id == decision_id)
    ).scalars().all()
