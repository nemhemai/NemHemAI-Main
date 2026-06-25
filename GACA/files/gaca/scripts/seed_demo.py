"""
End-to-end demo. Start the API (uvicorn app.main:app --reload), then run:
    python scripts/seed_demo.py

Posts an Entitlement decision and a Verification result through the 8-stage
workflow, then exercises explainability, replay, RTI, timeline, reports, dashboard.
"""
import httpx

BASE = "http://localhost:8000"

entitlement_event = {
    "event_type": "eligibility_decision",
    "responsible_agent": "entitlement",
    "citizen_id": "CIT-100045",
    "decision_id": "DEC-PMAY-001",
    "application_id": "APP-2026-0091",
    "scheme_id": "PMAY",
    "decision_type": "eligibility",
    "decision_result": "Eligible",
    "confidence_score": 0.92,
    "policy_id": "POL-PMAY-2026-04",
    "profile_snapshot": {"income": 180000, "house": "none", "state": "Maharashtra",
                          "reasons": ["Income below threshold", "No pucca house", "Maharashtra resident"]},
    "retrieved_context": {"reasons": ["Income below threshold", "No pucca house", "Maharashtra resident"]},
    "required_documents": ["Income Certificate", "Domicile Certificate"],
    "evidence_refs": [
        {"document_id": "DOC-IC-7781", "document_type": "Income Certificate",
         "role": "Income Verification", "verification_status": "pending"}
    ],
    "ai_metadata": {
        "llm": "ollama/llama3", "model_version": "2026-04",
        "prompt_template": "eligibility_v3", "embedding_model": "bge-small",
        "retrieved_context": {"clauses": ["PMAY-3.1"]},
        "generated_response": "Citizen meets PMAY income and housing criteria.",
        "confidence_score": 0.92, "safety_interventions": []
    }
}

verification_event = {
    "event_type": "verification_result",
    "responsible_agent": "verification",
    "citizen_id": "CIT-100045",
    "decision_id": "DEC-PMAY-001-VER",
    "application_id": "APP-2026-0091",
    "scheme_id": "PMAY",
    "decision_type": "verification",
    "decision_result": "Verified",
    "confidence_score": 0.97,
    "policy_id": "POL-PMAY-2026-04",
    "evidence_refs": [
        {"document_id": "DOC-DC-5521", "document_type": "Domicile Certificate",
         "role": "Residence Verification", "verification_status": "verified"}
    ]
}


def main():
    with httpx.Client(timeout=15) as c:
        print("Stage trace - Entitlement event:")
        for stage, data in c.post(f"{BASE}/events", json=entitlement_event).json().items():
            print(f"  {stage}: {data}")

        c.post(f"{BASE}/events", json=verification_event).raise_for_status()

        print("\nExplain DEC-PMAY-001:", c.get(f"{BASE}/explain/DEC-PMAY-001").json())
        print("\nReplay  DEC-PMAY-001:", c.get(f"{BASE}/replay/DEC-PMAY-001").json())
        print("\nTimeline CIT-100045:", c.get(f"{BASE}/timeline/CIT-100045").json())
        print("\nCompliance report:", c.get(f"{BASE}/reports/compliance").json())
        print("\nDashboard:", c.get(f"{BASE}/dashboard").json())


if __name__ == "__main__":
    main()
