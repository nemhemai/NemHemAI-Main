"""
GACA - Governance, Audit & Compliance Agent.
NemHem Platform Architecture Specification, Version 1.0.
"""
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.gaca import workflow
from app.agents.gaca.database import Base, engine, get_db
from app.agents.gaca.engines import (appeals, cross_department, dashboard, decision_audit,
                         decision_replay, explainability, fraud_graph,
                         human_override, policy_versioning, reporting, rti_support)
from app.agents.gaca.models import Citizen
from app.agents.gaca.schemas import GovernanceEventIn

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "gaca", "version": "1.0.0"}


# ---- Section 5: end-to-end workflow ----
@router.post("/events")
def ingest_event(event: GovernanceEventIn, db: Session = Depends(get_db)):
    return workflow.process_event(db, event)


# ---- 4.1 Decision Audit ----
@router.get("/decisions/citizen/{citizen_id}")
def decision_history(citizen_id: str, db: Session = Depends(get_db)):
    return [
        {
            "decision_id": d.decision_id,
            "citizen_id": d.citizen_id,
            "application_id": d.application_id,
            "scheme_id": d.scheme_id,
            "decision_type": d.decision_type,
            "decision_result": d.decision_result,
            "responsible_agent": d.responsible_agent,
            "confidence_score": d.confidence_score,
            "policy_id": d.policy_id,
            "timestamp": d.timestamp,
            "decision_trace": d.retrieved_context,
            "rule_results": d.retrieved_context.get("rule_results", []) if d.retrieved_context else [],
        }
        for d in decision_audit.decision_history(db, citizen_id)
    ]


# ---- 4.2 Policy Versioning ----
@router.get("/policies/{policy_name}/versions")
def policy_versions(policy_name: str, db: Session = Depends(get_db)):
    return [{"policy_id": p.policy_id, "rule_version": p.rule_version,
             "effective_date": p.effective_date} for p in policy_versioning.list_versions(db, policy_name)]


# ---- 4.6 Explainability ----
@router.get("/explain/{decision_id}")
def explain(decision_id: str, db: Session = Depends(get_db)):
    try:
        return explainability.explain_decision(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ---- 4.7 Human Override ----
@router.get("/overrides/{decision_id}")
def overrides(decision_id: str, db: Session = Depends(get_db)):
    return [o.override_id for o in human_override.overrides_for(db, decision_id)]


# ---- 4.10 Decision Replay ----
@router.get("/replay/{decision_id}")
def replay(decision_id: str, db: Session = Depends(get_db)):
    try:
        return decision_replay.replay(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ---- 4.13 Appeals ----
@router.post("/appeals")
def submit_appeal(decision_id: str, grounds: str | None = None, db: Session = Depends(get_db)):
    a = appeals.submit_appeal(db, decision_id, grounds)
    return {"appeal_id": a.appeal_id, "status": a.status}


# ---- 4.14 RTI Support ----
@router.get("/rti/{citizen_id}")
def rti(citizen_id: str, db: Session = Depends(get_db)):
    return rti_support.generate_rti_package(db, citizen_id)


# ---- 4.15 Cross-Department ----
@router.get("/timeline/{citizen_id}")
def timeline(citizen_id: str, db: Session = Depends(get_db)):
    return cross_department.citizen_timeline(db, citizen_id)


# ---- 4.16 Reporting ----
@router.get("/reports/{report_type}")
def report(report_type: str, citizen_id: str | None = None,
           application_id: str | None = None, department: str | None = None,
           db: Session = Depends(get_db)):
    params = {k: v for k, v in
              {"citizen_id": citizen_id, "application_id": application_id,
               "department": department}.items() if v is not None}
    try:
        r = reporting.generate_report(db, report_type, **params)
        return {"report_id": r.report_id, "report_type": r.report_type, "content": r.content}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---- 4.17 Governance Dashboard ----
@router.get("/dashboard")
def governance_dashboard(db: Session = Depends(get_db)):
    return dashboard.metrics(db)


# ---- 4.12 Fraud & Risk - Graph Analytics (Neo4j) ----
@router.get("/fraud/network")
def fraud_network(db: Session = Depends(get_db)):
    try:
        citizens = db.execute(select(Citizen)).scalars().all()
        synced = fraud_graph.sync_citizens(citizens)
        result = fraud_graph.fraud_networks()
        result["citizens_synced"] = synced
        return result
    except Exception as e:
        raise HTTPException(503, f"Neo4j not reachable or query failed: {e}")