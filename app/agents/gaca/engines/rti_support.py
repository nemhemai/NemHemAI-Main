"""4.14 RTI Support Engine - supports Right to Information requests.

Generates: decision summaries, evidence packages, officer actions, audit trails,
eligibility explanations.
"""
from sqlalchemy.orm import Session

from app.agents.gaca.engines import decision_audit, explainability, user_activity
from app.agents.gaca.engines.evidence_traceability import evidence_chain


def generate_rti_package(db: Session, citizen_id: str) -> dict:
    decisions = decision_audit.decision_history(db, citizen_id)

    decision_summaries = [{
        "decision_id": d.decision_id,
        "scheme_id": d.scheme_id,
        "decision_result": d.decision_result,
        "timestamp": d.timestamp.isoformat() if d.timestamp else None,
    } for d in decisions]

    evidence_packages = {
        d.decision_id: evidence_chain(db, d.decision_id) for d in decisions
    }
    eligibility_explanations = {
        d.decision_id: explainability.explain_decision(db, d.decision_id)
        for d in decisions
    }
    officer_actions = [{
        "action": e.action, "actor_id": e.actor_id,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
    } for e in user_activity.activity_log(db, actor_type="officer")]

    return {
        "citizen_id": citizen_id,
        "decision_summaries": decision_summaries,
        "evidence_packages": evidence_packages,
        "officer_actions": officer_actions,
        "audit_trail": [{"action": e.action, "actor_type": e.actor_type,
                         "timestamp": e.timestamp.isoformat() if e.timestamp else None}
                        for e in user_activity.activity_log(db)],
        "eligibility_explanations": eligibility_explanations,
    }
