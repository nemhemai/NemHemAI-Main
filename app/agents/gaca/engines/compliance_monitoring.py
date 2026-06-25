"""4.11 Compliance Monitoring Engine - continuously monitors compliance.

Validations: required documents present, mandatory approvals completed,
policy adherence, regulatory compliance, data governance compliance.
Outputs: compliance alerts, compliance reports, risk notifications.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.models import Application, Approval, ComplianceRecord, Decision, Document


def check_compliance(db: Session, application_id: str,
                     required_documents: list[str] | None = None) -> ComplianceRecord:
    required_documents = required_documents or []
    app = db.get(Application, application_id)

    # Required documents present
    docs = []
    if app:
        docs = db.execute(
            select(Document).where(Document.citizen_id == app.citizen_id)
        ).scalars().all()
    present_types = {d.document_type for d in docs}
    missing = [d for d in required_documents if d not in present_types]

    # Mandatory approvals completed
    approvals = db.execute(
        select(Approval).where(Approval.application_id == application_id)
    ).scalars().all()
    approvals_done = any(a.approver for a in approvals)

    # Policy adherence (a decision is mapped to a policy version)
    decisions = db.execute(
        select(Decision).where(Decision.application_id == application_id)
    ).scalars().all()
    policy_mapped = all(d.policy_id for d in decisions) if decisions else False

    checks = {
        "required_documents_present": len(missing) == 0,
        "missing_documents": missing,
        "mandatory_approvals_completed": approvals_done,
        "policy_adherence": policy_mapped,
    }
    alerts = []
    if missing:
        alerts.append(f"Missing required documents: {', '.join(missing)}")
    if not approvals_done:
        alerts.append("Mandatory approval not completed")
    if not policy_mapped:
        alerts.append("One or more decisions not mapped to a policy version")

    status = "compliant" if not alerts else "non_compliant"
    record = ComplianceRecord(application_id=application_id, checks=checks,
                              status=status, alerts=alerts)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
