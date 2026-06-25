"""4.9 AI Governance Engine - accountability for AI-generated outputs.

Tracks: LLM used, model version, prompt template, retrieval context, embedding
model, generated response, confidence score, safety interventions.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIGovernanceRecord


def record_ai_output(db: Session, decision_id: str, **fields) -> AIGovernanceRecord:
    row = AIGovernanceRecord(
        decision_id=decision_id,
        llm=fields.get("llm"),
        model_version=fields.get("model_version"),
        prompt_template=fields.get("prompt_template"),
        retrieved_context=fields.get("retrieved_context"),
        embedding_model=fields.get("embedding_model"),
        generated_response=fields.get("generated_response"),
        confidence_score=fields.get("confidence_score"),
        safety_interventions=fields.get("safety_interventions"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def ai_record(db: Session, decision_id: str) -> AIGovernanceRecord | None:
   return db.execute(
        select(AIGovernanceRecord).where(AIGovernanceRecord.decision_id == decision_id)
        .order_by(AIGovernanceRecord.record_id.desc())
    ).scalars().first()