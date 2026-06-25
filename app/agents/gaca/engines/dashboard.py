"""4.17 Governance Dashboard Engine - executive-level oversight.

Dashboard metrics (as listed): applications processed, approval rates, rejection
rates, fraud indicators, compliance violations, citizen satisfaction, department
performance, scheme utilization, officer productivity, appeal statistics, risk trends.
"""
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca.engines import fraud_risk
from app.agents.gaca.models import (Appeal, Application, ComplianceRecord, Decision,
                        RiskAssessment, Scheme)


def metrics(db: Session) -> dict:
    apps = db.execute(select(Application)).scalars().all()
    decisions = db.execute(select(Decision)).scalars().all()
    appeals = db.execute(select(Appeal)).scalars().all()
    compliance = db.execute(select(ComplianceRecord)).scalars().all()
    risks = db.execute(select(RiskAssessment)).scalars().all()

    results = [(d.decision_result or "").lower() for d in decisions]
    approvals = sum(1 for r in results if r in ("eligible", "approved", "verified"))
    rejections = sum(1 for r in results if r in ("not eligible", "rejected"))
    total_dec = len(decisions) or 1

    scheme_util = Counter(a.scheme_id for a in apps)
    dept_perf = Counter()
    for a in apps:
        scheme = db.get(Scheme, a.scheme_id)
        if scheme and scheme.department:
            dept_perf[scheme.department] += 1

    fraud = fraud_risk.detect_fraud(db)
    fraud_indicators = (len(fraud["duplicate_applications"])
                        + len(fraud["document_tampering"]))

    return {
        "applications_processed": len(apps),
        "approval_rate": round(approvals / total_dec, 3),
        "rejection_rate": round(rejections / total_dec, 3),
        "fraud_indicators": fraud_indicators,
        "compliance_violations": sum(1 for c in compliance if c.status == "non_compliant"),
        "citizen_satisfaction": None,        # source: citizen feedback (not yet captured)
        "department_performance": dict(dept_perf),
        "scheme_utilization": dict(scheme_util),
        "officer_productivity": None,        # source: officer throughput (not yet captured)
        "appeal_statistics": {
            "total": len(appeals),
            "final": sum(1 for a in appeals if a.status == "final"),
        },
        "risk_trends": {
            "assessments": len(risks),
            "avg_risk_score": round(sum(r.risk_score or 0 for r in risks) / (len(risks) or 1), 3),
        },
    }
