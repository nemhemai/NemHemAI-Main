"""
GACA - Governance, Audit & Compliance Agent.
NemHem Platform Architecture Specification, Version 1.0.

Routes expose the Section 5 workflow plus each Section 4 engine.
"""
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import workflow
from app.database import Base, engine, get_db
from app.engines import (appeals, cross_department, dashboard, decision_audit,
                         decision_replay, explainability, human_override,
                         policy_versioning, reporting, rti_support)
from app.schemas import GovernanceEventIn

app = FastAPI(title="GACA - Governance, Audit & Compliance Agent", version="1.0.0")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "gaca", "version": "1.0.0"}


# ---- Section 5: end-to-end workflow ----
@app.post("/events")
def ingest_event(event: GovernanceEventIn, db: Session = Depends(get_db)):
    """Run an inbound governance event through the 8-stage workflow."""
    return workflow.process_event(db, event)


# ---- 4.1 Decision Audit ----
@app.get("/decisions/citizen/{citizen_id}")
def decision_history(citizen_id: str, db: Session = Depends(get_db)):
    return [d.decision_id for d in decision_audit.decision_history(db, citizen_id)]


# ---- 4.2 Policy Versioning ----
@app.get("/policies/{policy_name}/versions")
def policy_versions(policy_name: str, db: Session = Depends(get_db)):
    return [{"policy_id": p.policy_id, "rule_version": p.rule_version,
             "effective_date": p.effective_date} for p in policy_versioning.list_versions(db, policy_name)]


# ---- 4.6 Explainability ----
@app.get("/explain/{decision_id}")
def explain(decision_id: str, db: Session = Depends(get_db)):
    try:
        return explainability.explain_decision(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ---- 4.7 Human Override ----
@app.get("/overrides/{decision_id}")
def overrides(decision_id: str, db: Session = Depends(get_db)):
    return [o.override_id for o in human_override.overrides_for(db, decision_id)]


# ---- 4.10 Decision Replay ----
@app.get("/replay/{decision_id}")
def replay(decision_id: str, db: Session = Depends(get_db)):
    try:
        return decision_replay.replay(db, decision_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# ---- 4.13 Appeals ----
@app.post("/appeals")
def submit_appeal(decision_id: str, grounds: str | None = None, db: Session = Depends(get_db)):
    a = appeals.submit_appeal(db, decision_id, grounds)
    return {"appeal_id": a.appeal_id, "status": a.status}


# ---- 4.14 RTI Support ----
@app.get("/rti/{citizen_id}")
def rti(citizen_id: str, db: Session = Depends(get_db)):
    return rti_support.generate_rti_package(db, citizen_id)


# ---- 4.15 Cross-Department ----
@app.get("/timeline/{citizen_id}")
def timeline(citizen_id: str, db: Session = Depends(get_db)):
    return cross_department.citizen_timeline(db, citizen_id)


# ---- 4.16 Reporting ----
@app.get("/reports/{report_type}")
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
@app.get("/dashboard")
def governance_dashboard(db: Session = Depends(get_db)):
    return dashboard.metrics(db)
