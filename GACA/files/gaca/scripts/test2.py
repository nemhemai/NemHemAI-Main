"""
Day 2 Test Script - GACA
-------------------------------------------------
Yeh 3 cheezein test karega:
1. Evidence Chain   - ek decision pe multiple documents
2. Policy Versioning - do alag policy versions
3. AI Governance    - query_audit jaisa full AI metadata

Chalane ka tarika:
    Step 1: uvicorn app.main:app --reload   (Terminal 1)
    Step 2: python scripts/test_day2.py     (Terminal 2)
"""

import httpx

BASE = "http://localhost:8000"

# ─────────────────────────────────────────────
# TEST 1 — Evidence Chain
# Ek decision pe 3 documents link kar ke dekhna
# ─────────────────────────────────────────────

evidence_chain_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-200010",
    "decision_id": "DEC-PMAY-EVID-001",
    "application_id": "APP-2026-0200",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Eligible",
    "confidence_score": 0.89,
    "policy_id": "POL-PMAY-2026-04",
    "profile_snapshot": {
        "income": 150000,
        "house": "none",
        "state": "Maharashtra"
    },
    "retrieved_context": {
        "clauses": ["PMAY-3.1", "PMAY-3.2"]
    },
    "required_documents": [
        "Income Certificate",
        "Domicile Certificate",
        "Aadhaar Card"
    ],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-1001",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified"
        },
        {
            "document_id": "DOC-DC-1002",
            "document_type": "Domicile Certificate",
            "role": "Residence Verification",
            "verification_status": "verified"
        },
        {
            "document_id": "DOC-AH-1003",
            "document_type": "Aadhaar Card",
            "role": "Identity Verification",
            "verification_status": "verified"
        }
    ],
    "ai_metadata": {
        "llm": "ollama/llama3",
        "model_version": "2026-04",
        "prompt_template": "eligibility_v3",
        "embedding_model": "bge-small",
        "retrieved_context": {"clauses": ["PMAY-3.1"]},
        "generated_response": "Citizen meets all PMAY criteria.",
        "confidence_score": 0.89,
        "safety_interventions": []
    }
}

# ─────────────────────────────────────────────
# TEST 2 — Policy Versioning
# Ek purani policy version aur ek nayi version
# ─────────────────────────────────────────────

policy_old_version_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-200011",
    "decision_id": "DEC-PMAY-POL-OLD",
    "application_id": "APP-2026-0201",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Eligible",
    "confidence_score": 0.85,
    "policy_id": "POL-PMAY-2025-01",   # <-- purani policy
    "profile_snapshot": {
        "income": 200000,
        "house": "none",
        "state": "Maharashtra"
    },
    "retrieved_context": {"clauses": ["PMAY-2.1"]},
    "required_documents": ["Income Certificate"],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-2001",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified"
        }
    ],
    "ai_metadata": {
        "llm": "ollama/llama3",
        "model_version": "2025-01",
        "prompt_template": "eligibility_v2",
        "embedding_model": "bge-small",
        "retrieved_context": {"clauses": ["PMAY-2.1"]},
        "generated_response": "Citizen eligible under old policy.",
        "confidence_score": 0.85,
        "safety_interventions": []
    }
}

policy_new_version_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-200012",
    "decision_id": "DEC-PMAY-POL-NEW",
    "application_id": "APP-2026-0202",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Not Eligible",
    "confidence_score": 0.91,
    "policy_id": "POL-PMAY-2026-04",   # <-- nayi policy
    "profile_snapshot": {
        "income": 200000,
        "house": "none",
        "state": "Maharashtra"
    },
    "retrieved_context": {"clauses": ["PMAY-3.1"]},
    "required_documents": ["Income Certificate"],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-2002",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified"
        }
    ],
    "ai_metadata": {
        "llm": "ollama/llama3",
        "model_version": "2026-04",
        "prompt_template": "eligibility_v3",
        "embedding_model": "bge-small",
        "retrieved_context": {"clauses": ["PMAY-3.1"]},
        "generated_response": "Citizen not eligible under new stricter policy.",
        "confidence_score": 0.91,
        "safety_interventions": []
    }
}

# ─────────────────────────────────────────────
# TEST 3 — AI Governance
# query_audit.py ke saare fields ke saath
# ─────────────────────────────────────────────

ai_governance_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-200013",
    "decision_id": "DEC-PMAY-AI-001",
    "application_id": "APP-2026-0203",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Eligible",
    "confidence_score": 0.95,
    "policy_id": "POL-PMAY-2026-04",
    "profile_snapshot": {
        "income": 120000,
        "house": "none",
        "state": "Maharashtra"
    },
    "retrieved_context": {
        "clauses": ["PMAY-3.1", "PMAY-3.2", "PMAY-4.1"]
    },
    "required_documents": ["Income Certificate", "Domicile Certificate"],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-3001",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified"
        },
        {
            "document_id": "DOC-DC-3002",
            "document_type": "Domicile Certificate",
            "role": "Residence Verification",
            "verification_status": "verified"
        }
    ],
    # query_audit.py ke fields yahan map ho rahe hain
    "ai_metadata": {
        "llm": "ollama/llama3",                          # query_audit: llm_model
        "model_version": "2026-04",
        "prompt_template": "eligibility_v3",
        "embedding_model": "bge-small",
        "retrieved_context": {                            # query_audit: retrieved_chunk_ids
            "clauses": ["PMAY-3.1", "PMAY-3.2"],
            "chunk_ids": ["CHK-001", "CHK-002", "CHK-003"]
        },
        "generated_response": "Citizen fully meets PMAY 2026 criteria with high confidence.",   # query_audit: response_text
        "confidence_score": 0.95,                        # query_audit: confidence
        "latency_ms": 342,                               # query_audit: latency_ms
        "safety_interventions": []
    }
}


# ─────────────────────────────────────────────
# MAIN — Sab test karo
# ─────────────────────────────────────────────

def main():
    with httpx.Client(timeout=15) as c:

        # ── Test 1: Evidence Chain ──
        print("\n" + "="*50)
        print("TEST 1 — Evidence Chain (3 documents)")
        print("="*50)
        resp = c.post(f"{BASE}/events", json=evidence_chain_event)
        for stage, data in resp.json().items():
            print(f"  {stage}: {data}")

        print("\nEvidence chain explain karo:")
        print(c.get(f"{BASE}/explain/DEC-PMAY-EVID-001").json())

        # ── Test 2: Policy Versioning ──
        print("\n" + "="*50)
        print("TEST 2 — Policy Versioning (purani vs nayi)")
        print("="*50)

        print("\nPurani policy (2025):")
        resp_old = c.post(f"{BASE}/events", json=policy_old_version_event)
        for stage, data in resp_old.json().items():
            print(f"  {stage}: {data}")

        print("\nNayi policy (2026):")
        resp_new = c.post(f"{BASE}/events", json=policy_new_version_event)
        for stage, data in resp_new.json().items():
            print(f"  {stage}: {data}")

        print("\nPurana decision replay (kaunsi policy thi tab):")
        print(c.get(f"{BASE}/replay/DEC-PMAY-POL-OLD").json())

        print("\nNaya decision replay:")
        print(c.get(f"{BASE}/replay/DEC-PMAY-POL-NEW").json())

        # ── Test 3: AI Governance ──
        print("\n" + "="*50)
        print("TEST 3 — AI Governance (query_audit fields)")
        print("="*50)
        resp_ai = c.post(f"{BASE}/events", json=ai_governance_event)
        for stage, data in resp_ai.json().items():
            print(f"  {stage}: {data}")

        print("\nAI decision explain:")
        print(c.get(f"{BASE}/explain/DEC-PMAY-AI-001").json())

        # ── Dashboard check ──
        print("\n" + "="*50)
        print("DASHBOARD — Updated metrics")
        print("="*50)
        print(c.get(f"{BASE}/dashboard").json())

        print("\n✅ Day 2 test complete!")


if __name__ == "__main__":
    main()