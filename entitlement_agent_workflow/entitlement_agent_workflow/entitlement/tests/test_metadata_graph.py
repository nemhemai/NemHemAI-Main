import os
import sys
import pytest
from neo4j import GraphDatabase
from app.core.metadata.graph_queries import (
    get_driver,
    get_scheme_rules,
    find_schemes_by_documents,
    find_schemes_by_rule_field,
    get_most_common_documents,
    find_related_schemes
)

def test_neo4j_connectivity():
    """Verify connectivity to Neo4j database."""
    try:
        driver = get_driver()
        driver.verify_connectivity()
        driver.close()
    except Exception as e:
        pytest.fail(f"Could not connect to Neo4j database: {e}")

def test_scheme_nodes_count():
    """Verify that exactly 20 Scheme nodes are present in the Neo4j graph."""
    query = "MATCH (s:Scheme) RETURN count(s) as count"
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query).single()
            count = result["count"]
            assert count == 20, f"Expected 20 Scheme nodes, but found {count} in the graph"

def test_requires_document_relationships():
    """Verify that every scheme requires at least one document."""
    query = """
    MATCH (s:Scheme)
    OPTIONAL MATCH (s)-[:REQUIRES_DOCUMENT]->(d:Document)
    RETURN s.scheme_id AS scheme_id, count(d) AS doc_count
    """
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                assert record["doc_count"] > 0, f"Scheme {record['scheme_id']} does not have any document requirements linked"

def test_exclusion_flag_roundtrip():
    """Verify that the is_exclusion flag is correctly indexed and queryable."""
    query = "MATCH (r:Rule {is_exclusion: true}) RETURN count(r) as count"
    with get_driver() as driver:
        with driver.session() as session:
            result = session.run(query).single()
            count = result["count"]
            # Assert that we have some exclusion rules (user requested verifying at least one)
            assert count > 0, "No rules with is_exclusion: true were found in the graph"
            
            # Fetch a known scheme rules and ensure the exclusion matches
            rules = get_scheme_rules("PM-KISAN-SCHEME")
            exclusions = [r for r in rules if r["is_exclusion"]]
            assert len(exclusions) > 0, "PM-KISAN-SCHEME should contain at least one exclusion rule"
            assert any(r["field"] == "pays_income_tax" for r in exclusions), "Expected pays_income_tax exclusion rule"

def test_find_schemes_by_documents():
    """Verify document matching logic handles fully and partially matched schemes."""
    # Run matching with Aadhaar and Bank passbook
    res = find_schemes_by_documents(["Aadhaar", "Bank passbook"])
    
    assert "fully_eligible" in res
    assert "partially_eligible" in res
    
    # We should have some fully eligible schemes (e.g. APY, PMSBY, PMJJBY only need Aadhaar and passbook)
    assert len(res["fully_eligible"]) > 0, "Expected at least one fully eligible scheme with Aadhaar & Bank passbook"
    
    # Verify the structure of the partial eligibility return shape
    for scheme in res["partially_eligible"]:
        assert "scheme_id" in scheme
        assert "scheme_name" in scheme
        assert "required_documents" in scheme
        assert "missing_documents" in scheme
        assert len(scheme["missing_documents"]) > 0, "Partially eligible scheme must list missing documents"
        assert "available_documents" in scheme

def test_find_schemes_by_rule_field():
    """Verify we can search for schemes validating specific fields."""
    res = find_schemes_by_rule_field("age")
    assert len(res) > 0, "Expected schemes checking 'age'"
    assert any(s["scheme_id"] == "PMUY-LPG" for s in res), "PMUY-LPG should check 'age'"

def test_get_most_common_documents():
    """Verify aggregation of common documents."""
    res = get_most_common_documents()
    assert len(res) > 0
    # The top one is almost certainly Aadhaar
    assert res[0]["document_name"] == "Aadhaar"
    assert res[0]["scheme_count"] >= 15

def test_find_related_schemes():
    """Verify finding related schemes by shared category or documents."""
    res = find_related_schemes("PM-SVANIDHI-EN")
    assert len(res) > 0
    # PM-SVANIDHI-HI should be related
    ids = [s["scheme_id"] for s in res]
    assert "PM-SVANIDHI-HI" in ids, "PM-SVANIDHI-HI should be related to PM-SVANIDHI-EN"
