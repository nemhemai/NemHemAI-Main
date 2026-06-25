"""4.6 Explainability Engine - human-readable explanations for decisions.

Explains: why approved, why rejected, which rules applied, which documents used,
which evidence influenced the outcome.
"""
from sqlalchemy.orm import Session

from app.engines import evidence_traceability
from app.models import AIGovernanceRecord, Decision, Policy
from sqlalchemy import select


def explain_decision(db: Session, decision_id: str) -> dict:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise ValueError("decision not found")

    chain = evidence_traceability.evidence_chain(db, decision_id)
    policy = db.get(Policy, decision.policy_id) if decision.policy_id else None
    ai = db.execute(
        select(AIGovernanceRecord).where(AIGovernanceRecord.decision_id == decision_id)
        .order_by(AIGovernanceRecord.record_id.desc())
    ).scalars().first()
    result = (decision.decision_result or "").lower()
    if result in ("eligible", "approved", "verified"):
        verdict = f"Approved/Eligible for {decision.scheme_id or 'the scheme'}."
    elif result in ("not eligible", "rejected"):
        verdict = f"Rejected/Not eligible for {decision.scheme_id or 'the scheme'}."
    else:
        verdict = f"Decision result: {decision.decision_result}."

    return {
        "decision_id": decision_id,
        "verdict": verdict,
        "reasons": (decision.retrieved_context or {}).get("reasons")
                   or (decision.profile_snapshot or {}).get("reasons"),
        "rules_applied": policy.rule_version if policy else None,
        "policy_used": policy.policy_name if policy else None,
        "documents_used": [c["document_type"] for c in chain],
        "evidence_influencing_outcome": chain,
        "confidence_score": decision.confidence_score,
        "ai_generated_response": ai.generated_response if ai else None,
    }
