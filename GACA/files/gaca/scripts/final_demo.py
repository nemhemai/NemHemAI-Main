"""
GACA - FINAL DEMO (showpiece).

Runs the whole Governance, Audit & Compliance Agent end-to-end as one story:
a citizen applies, the decision is recorded, explained, replayed, overridden,
approved, appealed; then a fraud ring tries to game the system and gets caught
(including a multi-hop ring via Neo4j); finally reports + dashboard.

Needs Postgres running (docker compose up -d). Neo4j too (for the ring section).
uvicorn does NOT need to be running.

Run:  .\\.venv\\Scripts\\python.exe scripts/final_demo.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app import workflow  # noqa: E402
from app.models import Citizen, Scheme  # noqa: E402
from app.schemas import AIMetadataIn, EvidenceRefIn, GovernanceEventIn  # noqa: E402
from app.engines import (appeals, approval_workflow, cross_department,  # noqa: E402
                         dashboard, decision_replay, explainability, fraud_graph,
                         fraud_risk, human_override, policy_versioning, reporting,
                         rti_support)


def hr(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Give the scheme a department + register a real policy version (nicer demo data)
if db.get(Scheme, "PMAY") is None:
    db.add(Scheme(scheme_id="PMAY", name="PM Awas Yojana", department="Housing"))
    db.commit()
policy_versioning.add_policy_version(
    db, policy_id="POL-PMAY-2026-04", policy_name="PMAY", circular_number="C-2026-04",
    rule_version="v3", effective_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
    issuing_authority="MoHUA")

hr("[1] CITIZEN APPLIES FOR PMAY  (8-stage workflow)")
ev = GovernanceEventIn(
    event_type="eligibility_decision", responsible_agent="entitlement",
    citizen_id="CIT-DEMO-001", decision_id="DEC-DEMO-001", application_id="APP-DEMO-001",
    scheme_id="PMAY", decision_type="eligibility", decision_result="Eligible",
    confidence_score=0.93, policy_id="POL-PMAY-2026-04",
    profile_snapshot={"income": 180000, "house": "none", "state": "Maharashtra",
                      "reasons": ["Income below threshold", "No pucca house", "Maharashtra resident"]},
    retrieved_context={"reasons": ["Income below threshold", "No pucca house", "Maharashtra resident"]},
    required_documents=["Income Certificate", "Domicile Certificate"],
    evidence_refs=[
        EvidenceRefIn(document_id="DOC-IC-1", document_type="Income Certificate",
                      role="Income Verification", verification_status="verified"),
        EvidenceRefIn(document_id="DOC-DC-1", document_type="Domicile Certificate",
                      role="Residence Verification", verification_status="verified"),
    ],
    ai_metadata=AIMetadataIn(llm="ollama/llama3", model_version="2026-04",
                             prompt_template="eligibility_v3", embedding_model="bge-small",
                             generated_response="Citizen meets PMAY 2026 criteria.",
                             confidence_score=0.93))
for stage, data in workflow.process_event(db, ev).items():
    print(f"  {stage}: {data}")

hr("[2] EXPLAINABILITY - why this decision?")
ex = explainability.explain_decision(db, "DEC-DEMO-001")
print("  Verdict:", ex["verdict"])
print("  Reasons:", ex["reasons"])
print("  Documents used:", ex["documents_used"])
print("  Confidence:", ex["confidence_score"])

hr("[3] DECISION REPLAY - reconstruct for audit / court")
rp = decision_replay.replay(db, "DEC-DEMO-001")
print("  Policy version:", rp["policy_version"])
print("  Model:", rp["model_version"], "| Prompt:", rp["prompt"])
print("  Result:", rp["decision_result"])

hr("[4] HUMAN OVERRIDE - officer reviews the AI decision")
ov = human_override.record_override(
    db, "DEC-DEMO-001", original_ai_recommendation="Eligible",
    officer_decision="Eligible (confirmed)", override_reason="Manually re-verified income proof",
    approval_authority="District Officer", supporting_notes="All documents cross-checked")
print("  By:", ov.approval_authority, "| reason:", ov.override_reason)

hr("[5] APPROVAL WORKFLOW - multi-level sign-off")
approval_workflow.record_approval(
    db, "APP-DEMO-001", reviewer="Clerk-A", approver="Officer-B",
    escalation_path=["Clerk-A", "Officer-B"], decision_rationale="Documents verified")
print("  Approvals:", [(a.reviewer, a.approver) for a in approval_workflow.workflow_for(db, "APP-DEMO-001")])

hr("[6] APPEAL - citizen appeals, resolved through stages")
ap = appeals.submit_appeal(db, "DEC-DEMO-001", grounds="Requesting higher subsidy slab")
for note, final in [("Under review", None), ("Reconsidered", None), ("Final", "Approved")]:
    ap = appeals.advance_appeal(db, ap.appeal_id, note=note, final_decision=final)
print("  Final appeal status:", ap.status, "| decision:", ap.final_decision)

hr("[7] FRAUD DETECTION - a fraud ring tries to game the system")
ring = [
    ("CIT-FR-1", "99 Link Road", "BANK-AAA", "MOB-111", None),
    ("CIT-FR-2", "99 Link Road", "BANK-999", "MOB-222", None),                 # shares address w/1
    ("CIT-FR-3", "55 Hill View", "BANK-999", "MOB-888", {"font_mismatch": True}),  # shares bank w/2 + tampered
    ("CIT-FR-4", "12 Park Lane", "BANK-BBB", "MOB-888", None),                 # shares mobile w/3
]
for i, (cid, addr, bank, mob, anom) in enumerate(ring, 1):
    workflow.process_event(db, GovernanceEventIn(
        event_type="eligibility_decision", responsible_agent="entitlement",
        citizen_id=cid, decision_id=f"DEC-FR-{i}", application_id=f"APP-FR-{i}", scheme_id="PMAY",
        decision_type="eligibility", decision_result="Eligible", confidence_score=0.8,
        policy_id="POL-PMAY-2026-04",
        profile_snapshot={"address": addr, "bank_account": bank, "mobile": mob},
        evidence_refs=[EvidenceRefIn(document_id=f"DOC-FR-{i}", document_type="Income Certificate",
                                     role="Income Verification", verification_status="verified",
                                     anomaly_indicators=anom)]))
# a duplicate application for CIT-FR-1
workflow.process_event(db, GovernanceEventIn(
    event_type="eligibility_decision", responsible_agent="entitlement",
    citizen_id="CIT-FR-1", decision_id="DEC-FR-1B", application_id="APP-FR-1B", scheme_id="PMAY",
    decision_type="eligibility", decision_result="Eligible", confidence_score=0.8,
    policy_id="POL-PMAY-2026-04",
    profile_snapshot={"address": "99 Link Road", "bank_account": "BANK-AAA", "mobile": "MOB-111"},
    evidence_refs=[]))
fr = fraud_risk.detect_fraud(db)
print("  Duplicate applications:", fr["duplicate_applications"])
print("  Document tampering:", fr["document_tampering"])
print("  Shared addresses:", fr["shared_attributes"]["shared_addresses"])

hr("[8] NEO4J FRAUD RING - multi-hop relationship network")
try:
    fraud_graph.sync_citizens(db.execute(select(Citizen)).scalars().all())
    net = fraud_graph.fraud_networks()
    for r in net["fraud_rings"]:
        print("  RING:", r)
    print("  Total rings detected:", net["ring_count"])
except Exception as e:
    print("  (Neo4j not reachable - start it with 'docker compose up -d'):", e)

hr("[9] REPORTS")
for rt in ["fraud_investigation", "executive_governance"]:
    rep = reporting.generate_report(db, rt)
    print(f"  {rt}: generated (report_id={rep.report_id})")

hr("[10] RTI PACKAGE - transparency on demand")
print("  Sections:", list(rti_support.generate_rti_package(db, "CIT-DEMO-001").keys()))

hr("[11] CITIZEN TIMELINE - cross-department")
print(" ", cross_department.citizen_timeline(db, "CIT-DEMO-001"))

hr("[12] GOVERNANCE DASHBOARD - final metrics")
m = dashboard.metrics(db)
for k in ["applications_processed", "approval_rate", "rejection_rate",
          "fraud_indicators", "compliance_violations"]:
    print(f"  {k}: {m[k]}")

print("\n" + "=" * 60)
print("  GACA FINAL DEMO COMPLETE - all engines demonstrated")
print("=" * 60)