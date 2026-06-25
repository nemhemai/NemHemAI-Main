"""
Day 4 - Fraud & Risk test.

Posts events that should trip every fraud check, then asks GACA to report fraud:
  1. Two citizens (A and B) sharing the SAME address, mobile, bank account
     -> shared-attribute clusters
  2. Citizen A applies for PMAY TWICE (two applications)
     -> duplicate application
  3. Citizen B's document carries anomaly indicators
     -> document tampering

Run the API first (uvicorn ...), then:
    .\.venv\Scripts\python.exe scripts/seed_day4_fraud.py
"""
import httpx

BASE = "http://localhost:8000"

SHARED = {"address": "12 MG Road, Mumbai", "mobile": "9990001111", "bank_account": "BANK-555"}


def event(decision_id, citizen_id, application_id, profile_extra=None, anomaly=None):
    profile = {**SHARED, "income": 190000}
    if profile_extra:
        profile.update(profile_extra)
    ev = {
        "event_type": "eligibility_decision",
        "responsible_agent": "entitlement",
        "citizen_id": citizen_id,
        "decision_id": decision_id,
        "application_id": application_id,
        "scheme_id": "PMAY",
        "decision_type": "eligibility",
        "decision_result": "Eligible",
        "confidence_score": 0.9,
        "policy_id": "POL-PMAY-2026-04",
        "profile_snapshot": profile,
        "evidence_refs": [{
            "document_id": f"DOC-{application_id}",
            "document_type": "Income Certificate",
            "role": "Income Verification",
            "verification_status": "verified",
            "anomaly_indicators": anomaly,
        }],
    }
    return ev


def main():
    with httpx.Client(timeout=15) as c:
        # Citizen A - two applications for the same scheme => duplicate
        c.post(f"{BASE}/events", json=event("DEC-FA-1", "CIT-FRAUD-A", "APP-FA-1")).raise_for_status()
        c.post(f"{BASE}/events", json=event("DEC-FA-2", "CIT-FRAUD-A", "APP-FA-2")).raise_for_status()
        print("Citizen A: 2 applications posted (duplicate expected).")

        # Citizen B - same address/mobile/bank as A, plus a tampered document
        c.post(f"{BASE}/events", json=event(
            "DEC-FB-1", "CIT-FRAUD-B", "APP-FB-1",
            anomaly={"font_mismatch": True, "edited_region": "income_field"},
        )).raise_for_status()
        print("Citizen B: posted, sharing A's address/mobile/bank + tampered document.\n")

        # Ask GACA to report fraud
        fraud = c.get(f"{BASE}/reports/fraud_investigation").json()["content"]
        print("=" * 50)
        print("FRAUD INVESTIGATION REPORT")
        print("=" * 50)
        print("Duplicate applications:", fraud["duplicate_applications"])
        print("Document tampering:", fraud["document_tampering"])
        print("Shared addresses:", fraud["shared_attributes"]["shared_addresses"])
        print("Shared bank accounts:", fraud["shared_attributes"]["shared_bank_accounts"])
        print("Shared mobile numbers:", fraud["shared_attributes"]["shared_mobile_numbers"])

        dash = c.get(f"{BASE}/dashboard").json()
        print("\nDashboard fraud_indicators:", dash["fraud_indicators"])
        print("\n[OK] Day 4 fraud test complete.")


if __name__ == "__main__":
    main()