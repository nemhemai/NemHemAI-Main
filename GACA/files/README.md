# GACA — Governance, Audit & Compliance Agent

NemHem Platform Architecture Specification, Version 1.0 ka implementation.
Code bilkul doc ke hisaab se hai — Section 4 ke 17 engines, Section 5 ka 8-stage
workflow, Section 6 ka data model, Section 7 ke integration points. Kuch extra nahi.

## Chalane ke steps

```bash
docker compose up -d                 # Postgres + Neo4j
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload        # tables auto-create
```

Naya terminal:
```bash
python scripts/seed_demo.py
```

API docs: http://localhost:8000/docs

## Doc → code mapping

### Section 4 — Core Functional Modules (engines)

| Doc | Engine | File |
|-----|--------|------|
| 4.1 | Decision Audit | `app/engines/decision_audit.py` |
| 4.2 | Policy Versioning | `app/engines/policy_versioning.py` |
| 4.3 | Evidence Traceability | `app/engines/evidence_traceability.py` |
| 4.4 | Document Audit | `app/engines/document_audit.py` |
| 4.5 | User Activity Audit | `app/engines/user_activity.py` |
| 4.6 | Explainability | `app/engines/explainability.py` |
| 4.7 | Human Override Governance | `app/engines/human_override.py` |
| 4.8 | Approval Workflow Governance | `app/engines/approval_workflow.py` |
| 4.9 | AI Governance | `app/engines/ai_governance.py` |
| 4.10 | Decision Replay | `app/engines/decision_replay.py` |
| 4.11 | Compliance Monitoring | `app/engines/compliance_monitoring.py` |
| 4.12 | Fraud & Risk Intelligence | `app/engines/fraud_risk.py` |
| 4.13 | Appeals & Reconsideration | `app/engines/appeals.py` |
| 4.14 | RTI Support | `app/engines/rti_support.py` |
| 4.15 | Cross-Department Governance | `app/engines/cross_department.py` |
| 4.16 | Governance Reporting | `app/engines/reporting.py` |
| 4.17 | Governance Dashboard | `app/engines/dashboard.py` |

### Baaki sections

| Doc | Kya | Kahan |
|-----|-----|-------|
| Section 5 — 8-stage End-to-End Workflow | `app/workflow.py` (`process_event`) |
| Section 6 — Data Model (saari entities) | `app/models.py` |
| Section 7 — Integration Points (inbound contract) | `app/schemas.py` (`GovernanceEventIn`) |

### Section 5 ke 8 stages (workflow mein)

1. Event Generation → inbound event
2. Audit Capture → 4.1, 4.5, 4.9
3. Evidence Association → 4.4, 4.3
4. Policy Mapping → 4.2
5. Compliance Validation → 4.11
6. Risk Evaluation → 4.12
7. Governance Recording → immutable record (integrity hash, Stage 7 "immutable")
8. Reporting & Analytics → 4.16, 4.17

## Integration (Section 7)

- **Entitlement Agent** → eligibility decisions / recommendations bhejhta hai (`/events`)
- **Verification Agent** → verification results / fraud indicators bhejhta hai (`/events`)
- **Neo4j** → Fraud & Risk graph (4.12), docker-compose mein ready
- **LlamaIndex / Hermes** → doc mein RAG / decision-memory ke liye named; yeh tumhare
  teammate ka RAG part hai. `retrieved_context` aur `policy_id` fields us seam ke liye hain.

## Note

Section 4.12 graph analytics abhi relational store par chalte hain taaki out-of-the-box
chale; production graph (relationship networks) ke liye Neo4j backend doc ke hisaab se
hai aur docker-compose mein ready khada hai.
