import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.agents.entitlement.services.entitlement_service import entitlement_agent

test_queries = [
    # 1. Ideal Match for PMAY-U
    "I earn ₹2,50,000 annually and live in an urban slum in Mumbai. I do not own any pucca house. What scheme can I apply for?",
    
    # 2. Ineligible Match for PMAY-U (Income too high)
    "I live in a city, don't own a pucca house, but I earn ₹25,00,000 a year. Can I get PMAY-U?",
    
    # 3. Ineligible Match for PMAY-U (Already owns pucca house)
    "I earn ₹7,00,000 a year and I already own a pucca house in Delhi. Can I get the PMAY subsidy?",
    
    # 4. Ideal Match for PM SVANidhi
    "I am a street vendor in Mumbai. I have my vending certificate and Aadhaar linked bank account.",
    
    # 5. Missing Information (Needs clarification - usually results in PENDING_VERIFICATION)
    "I am a street vendor from Maharashtra. What schemes am I eligible for?",
    
    # 6. Ideal Match for PM-KISAN (Farmer)
    "I am a farmer from rural Maharashtra. I own 1.5 hectares of land and have an active bank account.",
    
    # 7. Ineligible Match for PM-KISAN (Government employee/pays income tax)
    "I am a farmer with 1 acre of land but I am also a government employee and I pay income tax.",
    
    # 8. Out of Scope Query
    "What is the stock price of Nvidia today?"
]

def run_tests():
    print("=" * 80)
    print("Entitlement Engine Test Script")
    print("=" * 80)
    print("Running queries through the entitlement engine...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}:\nQuery: \"{query}\"")
        try:
            result = entitlement_agent(query)
            
            determination = result.get("determination", {})
            if determination.get("verdict") == "OUT_OF_SCOPE":
                print(f"  -> Result: OUT_OF_SCOPE")
                print(f"  -> Reason: {determination.get('explanation', {}).get('reasoning')}")
            else:
                schemes = determination.get("schemes", [])
                if not schemes:
                    print("  -> Result: No matching schemes found.")
                else:
                    for scheme in schemes[:3]: # Only show top 3 schemes
                        name = scheme.get("scheme_name", "Unknown")
                        verdict = scheme.get("verdict", "Unknown")
                        print(f"  -> Scheme: {name} | Verdict: {verdict}")
                        
        except Exception as e:
            print(f"  -> ERROR processing query: {e}")
        
        print("-" * 80)
        
if __name__ == "__main__":
    run_tests()
