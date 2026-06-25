"""4.16 Governance Reporting Engine - generates governance and compliance reports.

Reports: Citizen Audit, Application Audit, Department Audit, Fraud Investigation,
Compliance, Appeal History, AI Governance, Executive Governance.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.engines import decision_audit, fraud_risk
from app.agents.gaca.engines.cross_department import citizen_timeline
from app.agents.gaca.models import (AIGovernanceRecord, Appeal, Application, ComplianceRecord,
                        Decision, GovernanceReport, Scheme)

REPORT_TYPES = [
    "citizen_audit", "application_audit", "department_audit",
    "fraud_investigation", "compliance", "appeal_history",
    "ai_governance", "executive_governance",
]


def _content(db: Session, report_type: str, **params) -> dict:
    if report_type == "citizen_audit":
        cid = params["citizen_id"]
        return {"citizen_id": cid,
                "decisions": [d.decision_id for d in decision_audit.decision_history(db, cid)],
                "timeline": citizen_timeline(db, cid)}

    if report_type == "application_audit":
        aid = params["application_id"]
        return {"application_id": aid,
                "decisions": [d.decision_id for d in decision_audit.audit_records(db, aid)]}

    if report_type == "department_audit":
        dept = params["department"]
        schemes = db.execute(select(Scheme).where(Scheme.department == dept)).scalars().all()
        return {"department": dept, "schemes": [s.scheme_id for s in schemes]}

    if report_type == "fraud_investigation":
        return fraud_risk.detect_fraud(db)

    if report_type == "compliance":
        recs = db.execute(select(ComplianceRecord)).scalars().all()
        return {"total": len(recs),
                "non_compliant": [r.record_id for r in recs if r.status == "non_compliant"]}

    if report_type == "appeal_history":
        appeals = db.execute(select(Appeal)).scalars().all()
        return {"appeals": [{"appeal_id": a.appeal_id, "decision_id": a.decision_id,
                             "status": a.status, "final_decision": a.final_decision}
                            for a in appeals]}

    if report_type == "ai_governance":
        recs = db.execute(select(AIGovernanceRecord)).scalars().all()
        return {"records": [{"decision_id": r.decision_id, "llm": r.llm,
                             "model_version": r.model_version,
                             "safety_interventions": r.safety_interventions} for r in recs]}

    if report_type == "executive_governance":
        return {
            "applications": db.execute(select(Application)).scalars().all().__len__(),
            "decisions": db.execute(select(Decision)).scalars().all().__len__(),
            "fraud": fraud_risk.detect_fraud(db),
        }

    raise ValueError(f"unknown report_type: {report_type}")


def generate_report(db: Session, report_type: str, **params) -> GovernanceReport:
    if report_type not in REPORT_TYPES:
        raise ValueError(f"unknown report_type: {report_type}")
    report = GovernanceReport(report_type=report_type,
                              content=_content(db, report_type, **params))
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
