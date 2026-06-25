"""
Section 6 - Data Model.

Core entities, exactly as listed in the spec:
Citizen, Application, Scheme, Policy, Rule, Evidence, Document, Decision,
Approval, Appeal, Audit Event, Risk Assessment, Compliance Record, Governance Report.

HumanOverride (4.7) and AIGovernanceRecord (4.9) are added because the spec lists
their stored fields explicitly under those engines.

Fields on each entity are taken directly from the engine sections that name them.
JSON columns use SQLAlchemy's generic JSON type (works on Postgres and SQLite).
"""
from datetime import datetime, timezone

from sqlalchemy import (JSON, BigInteger, Column, DateTime, Float, ForeignKey,
                        Integer, String)

from app.agents.gaca.database import Base

# BIGINT on Postgres, but plain INTEGER on SQLite so autoincrement works there too.
PK = BigInteger().with_variant(Integer, "sqlite")


def _now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- Citizen
class Citizen(Base):
    __tablename__ = "citizen"
    citizen_id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    mobile = Column(String, nullable=True)          # used by Fraud & Risk graph (4.12)
    address = Column(String, nullable=True)         # used by Fraud & Risk graph (4.12)
    bank_account = Column(String, nullable=True)     # used by Fraud & Risk graph (4.12)
    profile = Column(JSON, nullable=True)            # snapshot for Decision Replay (4.10)


# ---------------------------------------------------------------- Scheme
class Scheme(Base):
    __tablename__ = "scheme"
    scheme_id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    department = Column(String, nullable=True)       # Cross-Department Governance (4.15)


# ---------------------------------------------------------------- Application
class Application(Base):
    __tablename__ = "application"
    application_id = Column(String, primary_key=True)
    citizen_id = Column(String, ForeignKey("citizen.citizen_id"), index=True)
    scheme_id = Column(String, ForeignKey("scheme.scheme_id"), index=True)
    status = Column(String, nullable=True)
    submitted_at = Column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------- Policy (4.2)
class Policy(Base):
    __tablename__ = "policy"
    policy_id = Column(String, primary_key=True)
    policy_name = Column(String, nullable=False)
    circular_number = Column(String, nullable=True)
    rule_version = Column(String, nullable=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    issuing_authority = Column(String, nullable=True)


# ---------------------------------------------------------------- Rule (4.2)
class Rule(Base):
    __tablename__ = "rule"
    rule_id = Column(String, primary_key=True)
    policy_id = Column(String, ForeignKey("policy.policy_id"), index=True)
    description = Column(String, nullable=True)
    rule_version = Column(String, nullable=True)


# ---------------------------------------------------------------- Document (4.4)
class Document(Base):
    __tablename__ = "document"
    document_id = Column(String, primary_key=True)
    citizen_id = Column(String, ForeignKey("citizen.citizen_id"), index=True)
    document_type = Column(String, nullable=True)
    upload_date = Column(DateTime(timezone=True), default=_now)
    verification_status = Column(String, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    verification_results = Column(JSON, nullable=True)
    anomaly_indicators = Column(JSON, nullable=True)


# ---------------------------------------------------------------- Decision (4.1)
class Decision(Base):
    __tablename__ = "decision"
    decision_id = Column(String, primary_key=True)
    citizen_id = Column(String, ForeignKey("citizen.citizen_id"), index=True)
    application_id = Column(String, ForeignKey("application.application_id"), index=True)
    scheme_id = Column(String, ForeignKey("scheme.scheme_id"), index=True)
    decision_type = Column(String, nullable=True)
    decision_result = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_now)
    responsible_agent = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    # Stage 4 Policy Mapping + Decision Replay (4.10) snapshots:
    policy_id = Column(String, ForeignKey("policy.policy_id"), nullable=True)
    profile_snapshot = Column(JSON, nullable=True)
    retrieved_context = Column(JSON, nullable=True)


# ---------------------------------------------------------------- Evidence (4.3)
class Evidence(Base):
    __tablename__ = "evidence"
    evidence_id = Column(PK, primary_key=True, autoincrement=True)
    decision_id = Column(String, ForeignKey("decision.decision_id"), index=True)
    document_id = Column(String, ForeignKey("document.document_id"), index=True)
    role = Column(String, nullable=True)   # e.g. "Income Verification" in the chain


# ---------------------------------------------------------------- Approval (4.8)
class Approval(Base):
    __tablename__ = "approval"
    approval_id = Column(PK, primary_key=True, autoincrement=True)
    application_id = Column(String, ForeignKey("application.application_id"), index=True)
    reviewer = Column(String, nullable=True)
    approver = Column(String, nullable=True)
    escalation_path = Column(JSON, nullable=True)
    approval_timestamp = Column(DateTime(timezone=True), default=_now)
    decision_rationale = Column(String, nullable=True)


# ---------------------------------------------------------------- Appeal (4.13)
class Appeal(Base):
    __tablename__ = "appeal"
    appeal_id = Column(PK, primary_key=True, autoincrement=True)
    decision_id = Column(String, ForeignKey("decision.decision_id"), index=True)
    status = Column(String, nullable=True)          # submission / review / reconsideration / final
    final_decision = Column(String, nullable=True)
    history = Column(JSON, nullable=True)


# ---------------------------------------------------------------- Audit Event (4.5 / Stage 2,7)
class AuditEvent(Base):
    __tablename__ = "audit_event"
    event_id = Column(PK, primary_key=True, autoincrement=True)
    actor_type = Column(String, nullable=False)     # citizen / officer / administrator / agent
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=_now)
    details = Column(JSON, nullable=True)
    integrity_hash = Column(String, nullable=True)  # Stage 7: immutable governance record


# ---------------------------------------------------------------- Risk Assessment (4.12)
class RiskAssessment(Base):
    __tablename__ = "risk_assessment"
    assessment_id = Column(PK, primary_key=True, autoincrement=True)
    subject_type = Column(String, nullable=False)   # citizen / application / officer / scheme
    subject_id = Column(String, nullable=False, index=True)
    risk_score = Column(Float, nullable=True)
    indicators = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------- Compliance Record (4.11)
class ComplianceRecord(Base):
    __tablename__ = "compliance_record"
    record_id = Column(PK, primary_key=True, autoincrement=True)
    application_id = Column(String, ForeignKey("application.application_id"), index=True)
    checks = Column(JSON, nullable=True)
    status = Column(String, nullable=True)          # compliant / non_compliant
    alerts = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)


# ---------------------------------------------------------------- Governance Report (4.16)
class GovernanceReport(Base):
    __tablename__ = "governance_report"
    report_id = Column(PK, primary_key=True, autoincrement=True)
    report_type = Column(String, nullable=False)
    generated_at = Column(DateTime(timezone=True), default=_now)
    content = Column(JSON, nullable=True)


# ---------------------------------------------------------------- Human Override (4.7)
class HumanOverride(Base):
    __tablename__ = "human_override"
    override_id = Column(PK, primary_key=True, autoincrement=True)
    decision_id = Column(String, ForeignKey("decision.decision_id"), index=True)
    original_ai_recommendation = Column(String, nullable=True)
    officer_decision = Column(String, nullable=True)
    override_reason = Column(String, nullable=True)
    approval_authority = Column(String, nullable=True)
    supporting_notes = Column(String, nullable=True)


# ---------------------------------------------------------------- AI Governance Record (4.9)
class AIGovernanceRecord(Base):
    __tablename__ = "ai_governance_record"
    record_id = Column(PK, primary_key=True, autoincrement=True)
    decision_id = Column(String, ForeignKey("decision.decision_id"), index=True)
    llm = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    prompt_template = Column(String, nullable=True)
    retrieved_context = Column(JSON, nullable=True)
    embedding_model = Column(String, nullable=True)
    generated_response = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    safety_interventions = Column(JSON, nullable=True)
