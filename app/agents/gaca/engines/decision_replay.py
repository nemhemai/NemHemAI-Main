"""4.10 Decision Replay Engine - reproduce a past decision exactly as it occurred.

Reconstructs: citizen profile, evidence, policy version, retrieved context,
model version, prompt, decision result.
"""
from sqlalchemy.orm import Session

from app.agents.gaca.engines import ai_governance, evidence_traceability
from app.agents.gaca.models import Decision, Policy


def replay(db: Session, decision_id: str) -> dict:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise ValueError("decision not found")

    policy = db.get(Policy, decision.policy_id) if decision.policy_id else None
    ai = ai_governance.ai_record(db, decision_id)

    return {
        "decision_id": decision_id,
        "citizen_profile": decision.profile_snapshot,
        "evidence": evidence_traceability.evidence_chain(db, decision_id),
        "policy_version": {
            "policy_name": policy.policy_name if policy else None,
            "rule_version": policy.rule_version if policy else None,
            "circular_number": policy.circular_number if policy else None,
        },
        "retrieved_context": decision.retrieved_context,
        "model_version": ai.model_version if ai else None,
        "prompt": ai.prompt_template if ai else None,
        "decision_result": decision.decision_result,
    }
