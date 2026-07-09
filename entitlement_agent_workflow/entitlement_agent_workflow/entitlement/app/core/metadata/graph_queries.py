import os
import sys
import argparse
from typing import Dict, List, Any
from neo4j import GraphDatabase

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Retrieve Neo4j credentials
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "nemhem_neo4j_password")

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def normalize_document_name(doc_name: str) -> str:
    """Normalize document name to title case and strip extra spaces."""
    return doc_name.strip().title()

def get_scheme_rules(scheme_id: str) -> List[Dict[str, Any]]:
    """
    Fetches the eligibility rules for a given scheme from Neo4j.
    Used by the evaluator.
    """
    query = """
    MATCH (s:Scheme {scheme_id: $scheme_id})-[:HAS_RULE]->(r:Rule)
    RETURN r.field AS field, r.operator AS operator, r.value AS value, r.is_exclusion AS is_exclusion
    """
    rules = []
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query, scheme_id=scheme_id)
            for record in result:
                rules.append({
                    "field": record["field"],
                    "operator": record["operator"],
                    "value": record["value"],
                    "is_exclusion": record["is_exclusion"]
                })
    return rules

def find_schemes_by_documents(available_docs: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns schemes that can be applied for based on the provided documents.
    Categorizes into fully_eligible (all required docs owned) and partially_eligible (some docs missing).
    """
    available_set = {normalize_document_name(doc) for doc in available_docs}
    
    query = """
    MATCH (s:Scheme)-[:REQUIRES_DOCUMENT]->(d:Document)
    RETURN s.scheme_id AS scheme_id, s.scheme_name AS scheme_name, collect(d.name) AS required_docs
    """
    
    fully_eligible = []
    partially_eligible = []
    
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                req_docs = record["required_docs"]
                
                # Check for match (comparing normalized names)
                missing = []
                available_present = []
                
                for doc in req_docs:
                    norm_doc = normalize_document_name(doc)
                    if norm_doc in available_set:
                        available_present.append(doc)
                    else:
                        missing.append(doc)
                        
                if not missing:
                    fully_eligible.append({
                        "scheme_id": record["scheme_id"],
                        "scheme_name": record["scheme_name"],
                        "required_documents": req_docs
                    })
                else:
                    partially_eligible.append({
                        "scheme_id": record["scheme_id"],
                        "scheme_name": record["scheme_name"],
                        "required_documents": req_docs,
                        "missing_documents": missing,
                        "available_documents": available_present
                    })
                    
    return {
        "fully_eligible": fully_eligible,
        "partially_eligible": partially_eligible
    }

def find_schemes_by_rule_field(field_name: str) -> List[Dict[str, Any]]:
    """Finds all schemes that contain rules checking a specific field."""
    query = """
    MATCH (s:Scheme)-[:HAS_RULE]->(r:Rule)-[:APPLIES_TO]->(rf:RuleField {name: $field_name})
    RETURN s.scheme_id AS scheme_id, s.scheme_name AS scheme_name, 
           r.operator AS operator, r.value AS value, r.is_exclusion AS is_exclusion
    """
    results = []
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query, field_name=field_name)
            for record in result:
                results.append({
                    "scheme_id": record["scheme_id"],
                    "scheme_name": record["scheme_name"],
                    "operator": record["operator"],
                    "value": record["value"],
                    "is_exclusion": record["is_exclusion"]
                })
    return results

def get_most_common_documents() -> List[Dict[str, Any]]:
    """Calculates document occurrence frequencies across all schemes."""
    query = """
    MATCH (s:Scheme)-[:REQUIRES_DOCUMENT]->(d:Document)
    RETURN d.name AS document_name, count(s) AS scheme_count
    ORDER BY scheme_count DESC
    """
    results = []
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                results.append({
                    "document_name": record["document_name"],
                    "scheme_count": record["scheme_count"]
                })
    return results

def find_related_schemes(scheme_id: str) -> List[Dict[str, Any]]:
    """Finds schemes related by category or shared document requirements."""
    query = """
    MATCH (s:Scheme {scheme_id: $scheme_id})
    MATCH (other:Scheme) WHERE other.scheme_id <> s.scheme_id
    OPTIONAL MATCH (s)-[:REQUIRES_DOCUMENT]->(d:Document)<-[:REQUIRES_DOCUMENT]-(other)
    WITH other, count(d) AS shared_docs_count,
         CASE WHEN other.category = s.category THEN 1 ELSE 0 END AS same_category
    WHERE shared_docs_count > 0 OR same_category = 1
    RETURN other.scheme_id AS scheme_id, other.scheme_name AS scheme_name, 
           other.category AS category, shared_docs_count, same_category
    ORDER BY same_category DESC, shared_docs_count DESC
    LIMIT 5
    """
    results = []
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query, scheme_id=scheme_id)
            for record in result:
                results.append({
                    "scheme_id": record["scheme_id"],
                    "scheme_name": record["scheme_name"],
                    "category": record["category"],
                    "shared_documents_count": record["shared_docs_count"],
                    "same_category": bool(record["same_category"])
                })
    return results

def main():
    parser = argparse.ArgumentParser(description="Query Neo4j Eligibility Graph")
    parser.add_argument("--query", type=str, required=True, 
                        choices=["rules", "match_docs", "by_field", "common_docs", "related"],
                        help="The graph query operation to run")
    parser.add_argument("--args", type=str, help="Arguments for the query (comma-separated if multiple)")
    
    args = parser.parse_args()
    
    if args.query == "rules":
        if not args.args:
            print("Error: --args <scheme_id> is required for 'rules' query.")
            sys.exit(1)
        rules = get_scheme_rules(args.args)
        print(f"\nEligibility rules for Scheme '{args.args}':")
        print("="*60)
        for r in rules:
            exc_str = " [EXCLUSION]" if r['is_exclusion'] else ""
            print(f"  Field: {r['field']:<20} | Operator: {r['operator']:<8} | Value: {str(r['value']):<15}{exc_str}")
        print(f"Total rules: {len(rules)}")
        
    elif args.query == "match_docs":
        if not args.args:
            available = []
        else:
            available = [doc.strip() for doc in args.args.split(",")]
        res = find_schemes_by_documents(available)
        
        print(f"\nScheme Eligibility Match results (Available docs: {available}):")
        print("="*80)
        print(f"FULLY ELIGIBLE SCHEMES ({len(res['fully_eligible'])}):")
        for s in res['fully_eligible']:
            print(f"  ✓ {s['scheme_name']} ({s['scheme_id']})")
            
        print("\nPARTIALLY ELIGIBLE SCHEMES (MISSING DOCUMENTS) (", len(res['partially_eligible']), "):")
        for s in res['partially_eligible']:
            missing_str = ", ".join(s['missing_documents'])
            print(f"  ✗ {s['scheme_name']} ({s['scheme_id']})")
            print(f"    Missing: {missing_str}")
            
    elif args.query == "by_field":
        if not args.args:
            print("Error: --args <field_name> is required for 'by_field' query.")
            sys.exit(1)
        res = find_schemes_by_rule_field(args.args)
        print(f"\nSchemes evaluating field '{args.args}':")
        print("="*80)
        for r in res:
            exc_str = " [EXCLUSION]" if r['is_exclusion'] else ""
            print(f"  - {r['scheme_name']} ({r['scheme_id']}) uses rule: {args.args} {r['operator']} {r['value']}{exc_str}")
            
    elif args.query == "common_docs":
        res = get_most_common_documents()
        print("\nMost Common Document Requirements:")
        print("="*50)
        for item in res:
            print(f"  {item['document_name']:<40} | Required by {item['scheme_count']} schemes")
            
    elif args.query == "related":
        if not args.args:
            print("Error: --args <scheme_id> is required for 'related' query.")
            sys.exit(1)
        res = find_related_schemes(args.args)
        print(f"\nSchemes related to '{args.args}':")
        print("="*80)
        for r in res:
            match_reason = []
            if r['same_category']:
                match_reason.append("same category")
            if r['shared_documents_count'] > 0:
                match_reason.append(f"{r['shared_documents_count']} shared documents")
            reason_str = " & ".join(match_reason)
            print(f"  - {r['scheme_name']} ({r['scheme_id']}) | Category: {r['category']} | Reason: {reason_str}")

if __name__ == "__main__":
    main()
