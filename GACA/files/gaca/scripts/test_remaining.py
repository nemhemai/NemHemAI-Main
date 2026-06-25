import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, SessionLocal, engine
import app.models
from app import workflow
from app.schemas import EvidenceRefIn, GovernanceEventIn
from app.engines import (appeals, approval_workflow, cross_department,
                         human_override, rti_support, user_activity)

print(">>> Remaining-engines test start")
Base.metadata.create_all(bind=engine)
db = SessionLocal()

ev = GovernanceEventIn(
    event_type="eligibility_decision", responsible_agent="entitlement",
    citizen_id="CIT-DAY5", decision_id="DEC-DAY5-001", application_id="APP-DAY5-001",
    scheme_id="PMAY", decision_type="eligibility", decision_result="Not Eligible",
    confidence_score=0.6, policy_id="POL-PMAY-2026-04",
    profile_snapshot={"income": 250000},
    evidence_refs=[EvidenceRefIn(document_id="DOC-DAY5-1", document_type="Income Certificate",
                                 role="Income Verification", verification_status="verified")],
)
workflow.process_event(db, ev)
print("Setup: decision DEC-DAY5-001 created.\n")

ov = human_override.record_override(
    db, "DEC-DAY5-001",
    original_ai_recommendation="Not Eligible", officer_decision="Eligible",
    override_reason="Income proof re-verified manually",
    approval_authority="District Officer",
    supporting_notes="Citizen submitted corrected income certificate")
print("4.7 Human Override   -> reason:", ov.override_reason)

approval_workflow.record_approval(
    db, "APP-DAY5-001", reviewer="Clerk-A", approver="Officer-B",
    escalation_path=["Clerk-A", "Officer-B"],
    decision_rationale="Documents verified, approved")
wf = approval_workflow.workflow_for(db, "APP-DAY5-001")
print("4.8 Approval Workflow -> reviewer/approver:", [(a.reviewer, a.approver) for a in wf])

ap = appeals.submit_appeal(db, "DEC-DAY5-001", grounds="Income was miscalculated")
ap = appeals.advance_appeal(db, ap.appeal_id, note="Under review")
ap = appeals.advance_appeal(db, ap.appeal_id, note="Reconsidered with new docs")
ap = appeals.advance_appeal(db, ap.appeal_id, note="Final decision", final_decision="Eligible")
print("4.13 Appeals        -> final status:", ap.status, "| final decision:", ap.final_decision)

rti = rti_support.generate_rti_package(db, "CIT-DAY5")
print("4.14 RTI Support     -> package sections:", list(rti.keys()))

acts = user_activity.activity_log(db)
print("4.5 User Activity    -> total events logged:", len(acts))

tl = cross_department.citizen_timeline(db, "CIT-DAY5")
print("4.15 Timeline        ->", tl)

print("\n[OK] All remaining engines tested! 17/17 engines now covered.")