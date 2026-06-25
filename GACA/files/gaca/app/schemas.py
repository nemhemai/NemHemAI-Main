"""
Integration contract (Section 7 - Integration Points).

What the Entitlement Agent (eligibility decisions, recommendation outcomes) and
Verification Agent (verification results, fraud indicators) send into GACA.
"""
from typing import Any

from pydantic import BaseModel, Field


class EvidenceRefIn(BaseModel):
    document_id: str
    document_type: str | None = None
    role: str | None = None                 # e.g. "Income Verification"
    verification_status: str | None = None
    anomaly_indicators: dict[str, Any] | None = None


class AIMetadataIn(BaseModel):
    llm: str | None = None
    model_version: str | None = None
    prompt_template: str | None = None
    retrieved_context: dict[str, Any] | None = None
    embedding_model: str | None = None
    generated_response: str | None = None
    confidence_score: float | None = None
    safety_interventions: list[str] | None = None


class GovernanceEventIn(BaseModel):
    event_type: str                          # eligibility_decision / verification_result / officer_action / ai_output
    responsible_agent: str                   # entitlement / verification / officer / system

    citizen_id: str
    decision_id: str
    application_id: str | None = None
    scheme_id: str | None = None
    decision_type: str | None = None
    decision_result: str | None = None
    confidence_score: float | None = None

    policy_id: str | None = None             # Stage 4: exact policy version used
    profile_snapshot: dict[str, Any] | None = None   # Stage 7 / Replay
    retrieved_context: dict[str, Any] | None = None
    required_documents: list[str] = Field(default_factory=list)

    evidence_refs: list[EvidenceRefIn] = Field(default_factory=list)
    ai_metadata: AIMetadataIn | None = None
