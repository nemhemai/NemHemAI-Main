"""
Day 3 Test Script - GACA
-------------------------------------------------
This script tests 2 things:
1. Human Override  - checking decision override
2. Appeals engine  - submitting appeal for rejected case

How to run:
    Step 1: uvicorn app.main:app --reload --port 8001   (Terminal 1)
    Step 2: python scripts/test_day3.py                 (Terminal 2)
"""

import httpx

BASE = "http://localhost:8001"


# ─────────────────────────────────────────────
# TEST 1 — Human Override
# Send a decision first, then check override
# ─────────────────────────────────────────────

decision_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-300001",
    "decision_id": "DEC-OVERRIDE-001",
    "application_id": "APP-2026-0301",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Eligible",
    "confidence_score": 0.78,
    "policy_id": "POL-PMAY-2026-04",
    "profile_snapshot": {
        "income": 175000,
        "house": "none",
        "state": "Maharashtra"
    },
    "retrieved_context": {"clauses": ["PMAY-3.1"]},
    "required_documents": ["Income Certificate", "Domicile Certificate"],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-4001",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified"
        },
        {
            "document_id": "DOC-DC-4002",
            "document_type": "Domicile Certificate",
            "role": "Residence Verification",
            "verification_status": "verified"
        }
    ],
    "ai_metadata": {
        "llm": "ollama/llama3",
        "model_version": "2026-04",
        "prompt_template": "eligibility_v3",
        "embedding_model": "bge-small",
        "retrieved_context": {"clauses": ["PMAY-3.1"]},
        "generated_response": "Citizen meets PMAY criteria.",
        "confidence_score": 0.78,
        "latency_ms": 290,
        "safety_interventions": []
    }
}


# ─────────────────────────────────────────────
# TEST 2 — Appeals Engine
# Send a rejected decision, then submit appeal
# ─────────────────────────────────────────────

rejected_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-300002",
    "decision_id": "DEC-APPEAL-001",
    "application_id": "APP-2026-0302",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Not Eligible",
    "confidence_score": 0.88,
    "policy_id": "POL-PMAY-2026-04",
    "profile_snapshot": {
        "income": 350000,
        "house": "owned",
        "state": "Maharashtra"
    },
    "retrieved_context": {"clauses": ["PMAY-3.1"]},
    "required_documents": ["Income Certificate"],
    "evidence_refs": [
        {
            "document_id": "DOC-IC-5001",
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
        "generated_response": "Citizen income exceeds PMAY limit. Not eligible.",
        "confidence_score": 0.88,
        "latency_ms": 310,
        "safety_interventions": []
    }
}

# Citizen is appealing against the rejection
appeal_payload = {
    "citizen_id": "CIT-300002",
    "reason": "Income certificate was incorrectly assessed. Actual income is 180000.",
    "supporting_documents": ["DOC-IC-5002"],
    "appeal_type": "income_dispute"
}


# ─────────────────────────────────────────────
# MAIN — Run all tests
# ─────────────────────────────────────────────

def main():
    with httpx.Client(timeout=15) as c:

        # ── Test 1: Human Override ──
        print("\n" + "="*50)
        print("TEST 1 — Human Override")
        print("="*50)

        print("\nStep 1 — Send decision event:")
        resp = c.post(f"{BASE}/events", json=decision_event)
        for stage, data in resp.json().items():
            print(f"  {stage}: {data}")

        print("\nStep 2 — Check override status (GET):")
        override_resp = c.get(f"{BASE}/overrides/DEC-OVERRIDE-001")
        print(f"  Override result: {override_resp.json()}")

        print("\nStep 3 — Explain decision:")
        print(c.get(f"{BASE}/explain/DEC-OVERRIDE-001").json())

        # ── Test 2: Appeals ──
        print("\n" + "="*50)
        print("TEST 2 — Appeals Engine")
        print("="*50)

        print("\nStep 1 — Send rejected decision:")
        resp2 = c.post(f"{BASE}/events", json=rejected_event)
        for stage, data in resp2.json().items():
            print(f"  {stage}: {data}")

        print("\nStep 2 — Submit appeal:")
        appeal_resp = c.post(
            f"{BASE}/appeals?decision_id=DEC-APPEAL-001",
            json=appeal_payload
        )
        print(f"  Appeal result: {appeal_resp.json()}")

        print("\nStep 3 — Check citizen timeline (is appeal tracked?):")
        print(c.get(f"{BASE}/timeline/CIT-300002").json())

        # ── Dashboard ──
        print("\n" + "="*50)
        print("DASHBOARD — Updated metrics")
        print("="*50)
        print(c.get(f"{BASE}/dashboard").json())

        print("\n✅ Day 3 test complete!")


if __name__ == "__main__":
    main()