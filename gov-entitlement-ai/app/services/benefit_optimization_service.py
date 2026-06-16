# app/services/benefit_optimization_service.py

from typing import Any

SCHEME_OPTIMIZATION_METADATA = {
    "PMAY-U": {
        "benefit_amount_val": 250000,
        "benefit_amount_desc": "₹2.5 Lakh Housing Subsidy",
        "benefit_score": 95,
        "probability_score": 80,
        "urgency_score": 70,
        "simplicity_score": 50,
        "complexity_desc": "High (requires no-pucca-house declaration, income verification, land registry mapping)"
    },
    "PM Awas Yojana": {
        "benefit_amount_val": 120000,
        "benefit_amount_desc": "₹1.2 Lakh Rural Housing Support",
        "benefit_score": 90,
        "probability_score": 80,
        "urgency_score": 70,
        "simplicity_score": 50,
        "complexity_desc": "High (requires SECC data mapping and Gram Panchayat approval)"
    },
    "PM SVANidhi": {
        "benefit_amount_val": 10000,
        "benefit_amount_desc": "₹10,000 - ₹50,000 Working Capital Loan (Interest Subsidized)",
        "benefit_score": 40,
        "probability_score": 95,
        "urgency_score": 90,
        "simplicity_score": 90,
        "complexity_desc": "Low (requires Certificate of Vending or ULB recommendation)"
    },
    "PM-KUSUM": {
        "benefit_amount_val": 150000,
        "benefit_amount_desc": "Solar Pump Installation Subsidy & Grid Feed-in Revenue",
        "benefit_score": 80,
        "probability_score": 70,
        "urgency_score": 60,
        "simplicity_score": 45,
        "complexity_desc": "High (requires land ownership deeds, DISCOM grid feasibility study)"
    },
    "Post-Matric Scholarship": {
        "benefit_amount_val": 50000,
        "benefit_amount_desc": "Academic tuition and maintenance fees reimbursement",
        "benefit_score": 60,
        "probability_score": 85,
        "urgency_score": 95,
        "simplicity_score": 75,
        "complexity_desc": "Medium (requires Caste and Income certificate, enrollment verification)"
    },
    "PM-KISAN": {
        "benefit_amount_val": 6000,
        "benefit_amount_desc": "₹6,000 yearly direct cash benefit (3 equal installments)",
        "benefit_score": 30,
        "probability_score": 98,
        "urgency_score": 80,
        "simplicity_score": 85,
        "complexity_desc": "Low (requires Aadhaar-seeded bank account and land deeds)"
    }
}

def optimize_benefits(eligible_schemes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Step 9: Benefit Optimization.
    Ranks schemes based on Benefit Amount (40%), Approval Probability (30%), Urgency (20%), and Simplicity (10%).
    Returns a ordered list with ranking breakdown and justifications.
    """
    ranked_schemes = []
    
    for item in eligible_schemes:
        scheme_name = item.get("scheme_name")
        meta = SCHEME_OPTIMIZATION_METADATA.get(scheme_name, {
            "benefit_amount_val": 5000,
            "benefit_amount_desc": "Varies",
            "benefit_score": 50,
            "probability_score": 50,
            "urgency_score": 50,
            "simplicity_score": 50,
            "complexity_desc": "Medium"
        })
        
        # Calculate weighted score
        overall_score = (
            (0.40 * meta["benefit_score"]) +
            (0.30 * meta["probability_score"]) +
            (0.20 * meta["urgency_score"]) +
            (0.10 * meta["simplicity_score"])
        )
        
        ranked_schemes.append({
            "scheme_name": scheme_name,
            "benefit_description": meta["benefit_amount_desc"],
            "overall_optimization_score": round(overall_score, 1),
            "benefit_amount_val": meta["benefit_amount_val"],
            "approval_probability": f"{meta['probability_score']}%",
            "urgency": "High" if meta["urgency_score"] >= 80 else ("Medium" if meta["urgency_score"] >= 60 else "Low"),
            "complexity": meta["complexity_desc"],
            "reason_for_order": f"Ranked with score {overall_score:.1f} due to high benefit value ({meta['benefit_amount_desc']}) and high operational urgency.",
            "readiness_score": item.get("readiness_score", 0),
            "application_readiness": item.get("application_readiness", "NEEDS_VERIFICATION"),
            "readiness_sublabel": item.get("readiness_sublabel", ""),
            "missing_docs_count": len(item.get("missing_documents", [])) if isinstance(item.get("missing_documents"), list) else 0,
        })
        
    # Sort by overall score descending
    ranked_schemes.sort(key=lambda s: s["overall_optimization_score"], reverse=True)
    
    # Assign actual ranking rank numbers
    for idx, s in enumerate(ranked_schemes):
        s["rank"] = idx + 1
        
    return ranked_schemes
