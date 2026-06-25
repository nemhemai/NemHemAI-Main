import httpx

print(">>> Neo4j fraud-ring test start")

BASE = "http://localhost:8000"


def event(decision_id, citizen_id, address, bank, mobile):
    return {
        "event_type": "eligibility_decision",
        "responsible_agent": "entitlement",
        "citizen_id": citizen_id,
        "decision_id": decision_id,
        "application_id": f"APP-{citizen_id}",
        "scheme_id": "PMAY",
        "decision_type": "eligibility",
        "decision_result": "Eligible",
        "confidence_score": 0.9,
        "policy_id": "POL-PMAY-2026-04",
        "profile_snapshot": {"address": address, "bank_account": bank, "mobile": mobile},
        "evidence_refs": [],
    }


def main():
    chain = [
        ("CIT-RING-1", "99 Link Road", "BANK-AAA", "MOB-111"),
        ("CIT-RING-2", "99 Link Road", "BANK-999", "MOB-222"),  # shares address with 1
        ("CIT-RING-3", "55 Hill View", "BANK-999", "MOB-888"),  # shares bank with 2
        ("CIT-RING-4", "12 Park Lane", "BANK-BBB", "MOB-888"),  # shares mobile with 3
    ]

    with httpx.Client(timeout=20) as c:
        for i, (cid, addr, bank, mob) in enumerate(chain, 1):
            c.post(f"{BASE}/events",
                   json=event(f"DEC-RING-{i}", cid, addr, bank, mob)).raise_for_status()
        print(f"Posted {len(chain)} citizens forming a multi-hop chain.\n")

        net = c.get(f"{BASE}/fraud/network").json()
        print("=" * 55)
        print("NEO4J FRAUD NETWORK (relationship analytics)")
        print("=" * 55)
        print("Citizens synced to graph:", net.get("citizens_synced"))
        print("\nDirect links (who shares what):")
        for link in net["direct_links"]:
            print(f"  {link['a']} <-> {link['b']}  via {link['attr']} = {link['value']}")
        print("\nFraud rings (connected groups, incl. multi-hop):")
        for ring in net["fraud_rings"]:
            print(f"  RING: {ring}")
        print("\nTotal rings detected:", net["ring_count"])
        print("\n[OK] Neo4j fraud-ring test complete.")


main()