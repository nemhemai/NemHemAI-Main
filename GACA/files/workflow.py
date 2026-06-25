"""
Section 5 - End-to-End Workflow.
"""
from sqlalchemy.orm import Session

from app.engines import (ai_governance, compliance_monitoring, decision_audit,
                         document_audit, evidence_traceability, fraud_risk,
                         policy_versioning, user_activity)
from app.models import Application, Citizen, Policy, Scheme
from app.schemas import GovernanceEventIn


def process_event(db: Session, event: GovernanceEventIn) -> dict:
    trace = {}

    # Stage 1 - Event Generation
    trace["stage_1_event_generation"] = {
        "event_type": event.event_type, "responsible_agent": event.responsible_agent,
        "decision_id": event.decision_id,
    }

    # Create stub rows for any referenced Citizen / Scheme / Application / Policy
    # so audit capture never fails on a missing reference.
    if db.get(Citizen, event.citizen_id) is None:
        db.add(Citizen(citizen_id=event.citizen_id, profile=event.profile_snapshot))
        db.commit()
    if event.scheme_id and db.get(Scheme, event.scheme_id) is None:
        db.add(Scheme(scheme_id=event.scheme_id, name=event.scheme_id))
        db.commit()
    if event.application_id and db.get(Application, event.application_id) is None:
        db.add(Application(application_id=event.application_id,
                           citizen_id=event.citizen_id, scheme_id=event.scheme_id,
                           status="received"))
        db.commit()
    if event.policy_id and db.get(Policy, event.policy_id) is None:
        db.add(Policy(policy_id=event.policy_id,
                      policy_name=event.scheme_id or event.policy_id))
        db.commit()

    # Stage 2 - Audit Capture
    decision = decision_audit.record_decision(
        db, decision_id=event.decision_id, citizen_id=event.citizen_id,
        application_id=event.application_id, scheme_id=event.scheme_id,
        decision_type=event.decision_type, decision_result=event.decision_result,
        responsible_agent=event.responsible_agent, confidence_score=event.confidence_score,
        policy_id=event.policy_id, profile_snapshot=event.profile_snapshot,
        retrieved_context=event.retrieved_context,
    )
    user_activity.log_activity(
        db, actor_type="agent", actor_id=event.responsible_agent,
        action=event.event_type, target=event.decision_id,
        details={"result": event.decision_result},
    )
    if event.ai_metadata is not None:
        ai_governance.record_ai_output(db, event.decision_id,
                                       **event.ai_metadata.model_dump())
    trace["stage_2_audit_capture"] = {"decision_recorded": decision.decision_id}

    # Stage 3 - Evidence Association
    associated = []
    for ref in event.evidence_refs:
        document_audit.record_document(
            db, document_id=ref.document_id, citizen_id=event.citizen_id,
            document_type=ref.document_type, verification_status=ref.verification_status,
            anomaly_indicators=ref.anomaly_indicators,
        )
        evidence_traceability.link_evidence(db, event.decision_id, ref.document_id,
                                            ref.role or "supporting")
        associated.append(ref.document_id)
    trace["stage_3_evidence_association"] = {"documents": associated}

    # Stage 4 - Policy Mapping
    policy = db.get(Policy, event.policy_id) if event.policy_id else None
    trace["stage_4_policy_mapping"] = {
        "policy_id": event.policy_id,
        "rule_version": policy.rule_version if policy else None,
    }

    # Stage 5 - Compliance Validation
    compliance = None
    if event.application_id:
        compliance = compliance_monitoring.check_compliance(
            db, event.application_id, required_documents=event.required_documents)
    trace["stage_5_compliance_validation"] = {
        "status": compliance.status if compliance else "skipped (no application_id)",
        "alerts": compliance.alerts if compliance else [],
    }

    # Stage 6 - Risk Evaluation
    fraud = fraud_risk.detect_fraud(db)
    indicators = {
        "duplicate_application": event.citizen_id in
            {k.split("::")[0] for k in fraud["duplicate_applications"]},
        "document_tampering": any(ref.anomaly_indicators for ref in event.evidence_refs),
    }
    risk = fraud_risk.score_subject(db, "citizen", event.citizen_id, indicators)
    trace["stage_6_risk_evaluation"] = {"risk_score": risk.risk_score,
                                        "indicators": indicators}

    # Stage 7 - Governance Recording (immutable record)
    record = user_activity.log_activity(
        db, actor_type="system", actor_id="gaca",
        action="governance_recording", target=event.decision_id,
        details={"decision_result": event.decision_result,
                 "compliance": compliance.status if compliance else None,
                 "risk_score": risk.risk_score},
    )
    trace["stage_7_governance_recording"] = {
        "event_id": record.event_id, "integrity_hash": record.integrity_hash}

    # Stage 8 - Reporting & Analytics
    trace["stage_8_reporting_analytics"] = {
        "available": ["GET /reports/{type}", "GET /dashboard"]}

    return trace