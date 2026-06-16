import pytest

from app.retrieval.entitlement import retrieve_entitlement_clauses


BENCHMARK_QUERIES = [
    ("street vendor vending certificate loan", "PM SVANidhi"),
    ("farmer solar pump component B kusum", "PM-KUSUM"),
    ("pm kisan cultivable land aadhaar bank account", "PM-KISAN"),
    ("post matric scholarship income scheduled caste student", "Post-Matric Scholarship"),
    ("urban housing pucca house ews beneficiary pmay", "PMAY-U"),
]


@pytest.mark.integration
@pytest.mark.parametrize(("query", "scheme_name"), BENCHMARK_QUERIES)
def test_scheme_filtered_entitlement_retrieval_returns_citations(db_conn, query, scheme_name):
    results = retrieve_entitlement_clauses(
        db_conn,
        query,
        scheme_name=scheme_name,
        language="en",
        top_k=3,
    )

    assert results, f"No retrieval results for {scheme_name}: {query}"
    assert all(result["scheme_name"] == scheme_name for result in results)

    top = results[0]
    assert top["chunk_id"]
    assert top["file_name"].endswith(".pdf")
    assert top["page_range"]
    assert top["text"]
    assert top["score"] > 0


@pytest.mark.integration
def test_entitlement_retrieval_can_filter_by_category(db_conn):
    results = retrieve_entitlement_clauses(
        db_conn,
        "farmer solar pump subsidy",
        scheme_category="agriculture_energy",
        language="en",
        top_k=5,
    )

    assert results
    assert {result["scheme_name"] for result in results} == {"PM-KUSUM"}
