import os
import sys
import json
from typing import List, Dict, Any

# Ensure mock key for LiteLLM / PraisonAI initialization
if "OPENAI_API_KEY" not in os.environ:
    os.environ["OPENAI_API_KEY"] = "mock-key"

# Imports from PraisonAI
from praisonaiagents import Agent, Task, AgentTeam

# Imports from entitlement app
from app.core.metadata.tools import (
    build_profile_tool,
    discover_schemes_tool,
    evaluate_eligibility_tool,
    verify_documents_stub,
    normalize_document_name
)


def run_eligibility_pipeline(
    citizen_data: dict, 
    search_query: str = None, 
    run_verification_agent: bool = True
) -> dict:
    """
    Intake citizen data → Build profile → Discover potential schemes →
    Evaluate eligibility → Run verification agent stub → Reconfirm eligibility.
    
    Returns a unified report dictionary.
    """
    report = {
        "citizen_id": citizen_data.get("citizen_id", "anonymous"),
        "initial_profile": None,
        "schemes_evaluated": {}
    }
    
    # 1. Intake and Profile Building
    try:
        profile = build_profile_tool(citizen_data)
        report["initial_profile"] = profile
    except Exception as e:
        report["error"] = f"Profile building failed: {e}"
        return report

    # 2. Scheme Discovery (Qdrant similarity + Neo4j document overlap)
    candidates = discover_schemes_tool(profile, query_text=search_query)
    
    # 3. Initial Evaluation & Verification Reconfirmation
    for scheme in candidates:
        scheme_id = scheme["scheme_id"]
        scheme_name = scheme["scheme_name"]
        
        # Initial evaluation (based on self-declared verified_documents)
        initial_eval = evaluate_eligibility_tool(profile, scheme_id)
        
        # Determine missing documents
        required_docs = scheme.get("required_documents", [])
        missing_docs = initial_eval.get("missing_documents", [])
        
        # Reconfirmation Step
        final_eval = initial_eval
        verification_status = "Skipped"
        verified_package = []
        
        if run_verification_agent and initial_eval["status"] == "PENDING_DOCS" and missing_docs:
            # Connect Verification Agent stub to verify missing documents
            verified_package = verify_documents_stub(profile["citizen_id"], missing_docs)
            
            if verified_package:
                # Build an updated profile combining original verified documents with newly verified ones
                updated_docs = list(set(profile.get("verified_documents", []) + verified_package))
                
                updated_profile = profile.copy()
                updated_profile["verified_documents"] = updated_docs
                
                # Reconfirm eligibility with the updated profile
                final_eval = evaluate_eligibility_tool(updated_profile, scheme_id)
                verification_status = f"Completed (Verified {len(verified_package)}/{len(missing_docs)} documents)"
            else:
                verification_status = "Completed (No additional documents verified)"
        
        # Save results for this scheme
        report["schemes_evaluated"][scheme_id] = {
            "scheme_name": scheme_name,
            "category": scheme.get("category"),
            "discovery_source": scheme.get("source"),
            "initial_status": initial_eval["status"],
            "verification_agent_run": verification_status,
            "newly_verified_documents": verified_package,
            "final_status": final_eval["status"],
            "missing_fields": final_eval.get("missing_fields", []),
            "missing_documents": final_eval.get("missing_documents", []),
            "reasons": final_eval.get("reason", "Evaluation complete.")
        }
        
    return report


def get_praison_agent(model_name: str = "ollama/llama3.1") -> Agent:
    """Instantiates and returns the PraisonAI Entitlement Agent."""
    return Agent(
        name="EntitlementAgent",
        role="Entitlement Specialist",
        goal="Discover government welfare schemes for a citizen and evaluate their eligibility status.",
        backstory="An expert AI policy advisor specializing in Indian government welfare schemes. "
                  "You help citizens discover matching benefits by validating their profiles against "
                  "strict scheme guidelines, using search tools and graph databases.",
        tools=[build_profile_tool, discover_schemes_tool, evaluate_eligibility_tool],
        llm=model_name
    )


def run_agent_pipeline(
    citizen_data: dict, 
    search_query: str = None, 
    model_name: str = "ollama/llama3.1"
) -> str:
    """
    Assembles the PraisonAI agent and runs a task to evaluate eligibility 
    interactively using local LLM orchestration.
    """
    agent = get_praison_agent(model_name)
    
    task_desc = f"""
    Evaluate scheme eligibility for the citizen with data: {json.dumps(citizen_data)}.
    The citizen's query search term is: '{search_query}'.
    Follow these steps:
    1. Build the validated Citizen 360 profile using build_profile_tool.
    2. Discover potential schemes using discover_schemes_tool with the query term.
    3. For each candidate scheme found, evaluate the citizen's eligibility status using evaluate_eligibility_tool.
    4. Compile a concise, professional assessment report listing the matching schemes, their eligibility status, and any missing fields or documents.
    """
    
    eval_task = Task(
        description=task_desc,
        expected_output="A structured report listing schemes, eligibility status, and missing requirements.",
        agent=agent
    )
    
    # Run orchestration
    agents = AgentTeam(agents=[agent], tasks=[eval_task])
    return agents.start()


if __name__ == "__main__":
    # Sample Test Intake data
    test_citizen = {
        "citizen_id": "c_street_vendor_poor",
        "age": 35,
        "income_annual": 120000,
        "state": "Maharashtra",
        "urban_rural": "urban",
        "occupation": "street_vendor",
        "category": "General",
        "verified_documents": ["Aadhaar"]
    }
    
    print("Running deterministic Eligibility Pipeline...")
    print("=" * 80)
    report = run_eligibility_pipeline(
        test_citizen, 
        search_query="schemes for street vendors needing loans"
    )
    
    print(f"Citizen ID: {report['citizen_id']}")
    print(f"Discovered and evaluated {len(report['schemes_evaluated'])} schemes:")
    for scheme_id, eval_data in report["schemes_evaluated"].items():
        print("-" * 60)
        print(f"Scheme ID:      {scheme_id}")
        print(f"Scheme Name:    {eval_data['scheme_name']}")
        print(f"Source:         {eval_data['discovery_source']}")
        print(f"Initial Status: {eval_data['initial_status']}")
        print(f"Verification:   {eval_data['verification_agent_run']}")
        print(f"Final Status:   {eval_data['final_status']}")
        if eval_data['missing_documents']:
            print(f"Missing Docs:   {', '.join(eval_data['missing_documents'])}")
        if eval_data['missing_fields']:
            print(f"Missing Fields: {', '.join(eval_data['missing_fields'])}")
    print("=" * 80)
