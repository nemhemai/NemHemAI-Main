import os
import sys
import yaml
import uuid
from pathlib import Path
from neo4j import GraphDatabase

# Configure stdout to use UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Retrieve Neo4j credentials from environment variables or use defaults
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "nemhem_neo4j_password")

def normalize_document_name(doc_name: str) -> str:
    """Normalize document name to title case and strip extra spaces."""
    return doc_name.strip().title()

def main():
    records_dir = Path(__file__).resolve().parent / "records"
    if not records_dir.exists():
        print(f"Records directory not found: {records_dir}")
        sys.exit(1)
        
    yaml_files = list(records_dir.glob("*.yaml"))
    print(f"Found {len(yaml_files)} YAML records to index in Neo4j.")
    
    if not yaml_files:
        print("No YAML files found. Run extract_rules.py first.")
        sys.exit(1)

    print(f"Connecting to Neo4j at {NEO4J_URI}...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

    with driver.session() as session:
        # Create Constraints if they do not exist (Neo4j 5.x syntax)
        print("Setting up Neo4j constraints...")
        try:
            session.run("CREATE CONSTRAINT scheme_id_unique IF NOT EXISTS FOR (s:Scheme) REQUIRE s.scheme_id IS UNIQUE")
            session.run("CREATE CONSTRAINT doc_name_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.name IS UNIQUE")
            session.run("CREATE CONSTRAINT field_name_unique IF NOT EXISTS FOR (rf:RuleField) REQUIRE rf.name IS UNIQUE")
        except Exception as e:
            print(f"Warning: Could not create constraints (might be due to database permissions or version): {e}")

        # Clear existing Scheme, Rule, and RuleField nodes, and their relationships
        print("Clearing existing schemes, rules, and rule fields...")
        session.run("MATCH (s:Scheme) DETACH DELETE s")
        session.run("MATCH (r:Rule) DETACH DELETE r")
        session.run("MATCH (rf:RuleField) DETACH DELETE rf")

        # Process each scheme record
        for yaml_file in yaml_files:
            print(f"Indexing: {yaml_file.name}")
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    scheme = yaml.safe_load(f)
            except Exception as e:
                print(f"Failed to parse {yaml_file.name}: {e}")
                continue

            scheme_id = scheme.get("scheme_id", yaml_file.stem)
            scheme_name = scheme.get("scheme_name", yaml_file.stem)
            
            # Map benefit values
            benefit = scheme.get("benefit", {})
            benefit_type = benefit.get("type")
            benefit_amount = benefit.get("amount", 0)
            benefit_currency = benefit.get("currency", "INR")

            # Extract tags as list of strings
            tags = scheme.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags] if tags else []

            # 1. Merge Scheme Node
            scheme_cypher = """
            MERGE (s:Scheme {scheme_id: $scheme_id})
            SET s.scheme_name = $scheme_name,
                s.category = $category,
                s.issuing_authority = $issuing_authority,
                s.department_code = $department_code,
                s.jurisdiction = $jurisdiction,
                s.state_origin = $state_origin,
                s.active = $active,
                s.benefit_type = $benefit_type,
                s.benefit_amount = $benefit_amount,
                s.benefit_currency = $benefit_currency,
                s.processing_days = $processing_days,
                s.application_url = $application_url,
                s.tags = $tags
            RETURN s
            """
            
            session.run(
                scheme_cypher,
                scheme_id=scheme_id,
                scheme_name=scheme_name,
                category=scheme.get("category"),
                issuing_authority=scheme.get("issuing_authority"),
                department_code=scheme.get("department_code"),
                jurisdiction=scheme.get("jurisdiction"),
                state_origin=scheme.get("state_origin"),
                active=scheme.get("active", True),
                benefit_type=benefit_type,
                benefit_amount=benefit_amount,
                benefit_currency=benefit_currency,
                processing_days=scheme.get("processing_days"),
                application_url=scheme.get("application_url"),
                tags=tags
            )

            # 2. Add Required Documents
            req_docs = scheme.get("required_documents", [])
            for doc in req_docs:
                norm_doc = normalize_document_name(doc)
                doc_cypher = """
                MATCH (s:Scheme {scheme_id: $scheme_id})
                MERGE (d:Document {name: $doc_name})
                MERGE (s)-[:REQUIRES_DOCUMENT]->(d)
                """
                session.run(doc_cypher, scheme_id=scheme_id, doc_name=norm_doc)

            # 3. Add Eligibility Rules & RuleFields
            rules = scheme.get("eligibility_rules", [])
            for rule in rules:
                field = rule.get("field")
                operator = rule.get("operator")
                value = rule.get("value")
                is_exclusion = rule.get("is_exclusion", False)

                # Generate a unique rule node ID to prevent cross-scheme collisions
                rule_node_id = f"{scheme_id}_{field}_{operator}_{str(uuid.uuid4())[:8]}"

                # Convert value to standard type if it's a list/dict to store cleanly
                if isinstance(value, (list, dict)):
                    # Neo4j supports list arrays if elements are homogeneous, but we keep it clean
                    pass

                rule_cypher = """
                MATCH (s:Scheme {scheme_id: $scheme_id})
                CREATE (r:Rule {
                    id: $rule_id,
                    field: $field,
                    operator: $operator,
                    value: $value,
                    is_exclusion: $is_exclusion
                })
                MERGE (s)-[:HAS_RULE]->(r)
                MERGE (rf:RuleField {name: $field})
                MERGE (r)-[:APPLIES_TO]->(rf)
                """
                session.run(
                    rule_cypher,
                    scheme_id=scheme_id,
                    rule_id=rule_node_id,
                    field=field,
                    operator=operator,
                    value=value,
                    is_exclusion=is_exclusion
                )

        # 4. Clean up orphaned documents (documents that are no longer required by any scheme)
        print("Cleaning up orphaned document nodes...")
        session.run("MATCH (d:Document) WHERE NOT (d)<-[:REQUIRES_DOCUMENT]-() DELETE d")
        
        # Verify counts in graph
        res_schemes = session.run("MATCH (s:Scheme) RETURN count(s) as count").single()
        res_docs = session.run("MATCH (d:Document) RETURN count(d) as count").single()
        res_rules = session.run("MATCH (r:Rule) RETURN count(r) as count").single()
        res_fields = session.run("MATCH (rf:RuleField) RETURN count(rf) as count").single()

        print("\nIndexing summary:")
        print(f"  Scheme nodes:     {res_schemes['count']}")
        print(f"  Document nodes:   {res_docs['count']}")
        print(f"  Rule nodes:       {res_rules['count']}")
        print(f"  RuleField nodes:  {res_fields['count']}")
        print("\nNeo4j indexing completed successfully!")

    driver.close()

if __name__ == "__main__":
    main()
