import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTITLEMENT_DIR = PROJECT_ROOT / "data" / "entitlement"

EXPECTED_SCHEMES = {
    "Operational-Guidelines-of-PMAY-U-2.pdf": "PMAY-U",
    "PM Awas Yojana (Housing).pdf": "PM Awas Yojana",
    "PM SVANidhi_English.pdf": "PM SVANidhi",
    "PM SVANidhi_Hindi.pdf": "PM SVANidhi",
    "PM-KUSUM (Farmer Solar Scheme).pdf": "PM-KUSUM",
    "Post-Matric Scholarship Scheme.pdf": "Post-Matric Scholarship",
    "Revised Operational Guidelines - PM-Kisan Scheme.pdf": "PM-KISAN",
}

REQUIRED_METADATA_FIELDS = {
    "title",
    "document_number",
    "issuing_authority",
    "department_code",
    "jurisdiction",
    "document_type",
    "security_level",
    "primary_language",
    "version_label",
    "scheme_name",
    "scheme_category",
    "agent_domain",
}


def test_entitlement_pdfs_have_matching_metadata_sidecars():
    for pdf_name, scheme_name in EXPECTED_SCHEMES.items():
        pdf_path = ENTITLEMENT_DIR / pdf_name
        meta_path = pdf_path.with_suffix(".json")

        assert pdf_path.exists(), f"Missing entitlement PDF: {pdf_name}"
        assert meta_path.exists(), f"Missing metadata JSON for {pdf_name}"

        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        assert REQUIRED_METADATA_FIELDS <= metadata.keys()
        assert metadata["agent_domain"] == "entitlement"
        assert metadata["scheme_name"] == scheme_name
        assert metadata["jurisdiction"] == "central"
        assert metadata["document_type"] == "guideline"
        assert metadata["security_level"] == "public"


@pytest.mark.integration
def test_entitlement_documents_are_registered_chunked_and_embedded(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                d.file_name,
                d.metadata->>'scheme_name' AS scheme_name,
                d.metadata->>'agent_domain' AS agent_domain,
                COUNT(DISTINCT e.element_id) AS elements,
                COUNT(DISTINCT c.chunk_id) AS chunks,
                COUNT(DISTINCT em.chunk_id) AS embeddings
            FROM documents d
            LEFT JOIN document_elements e ON e.document_id = d.document_id
            LEFT JOIN document_chunks c ON c.document_id = d.document_id
            LEFT JOIN document_embeddings em ON em.document_id = d.document_id
            WHERE d.file_name = ANY(%s)
            GROUP BY d.file_name, d.metadata
            ORDER BY d.file_name
            """,
            (list(EXPECTED_SCHEMES.keys()),),
        )
        rows = cur.fetchall()

    observed = {row[0]: row for row in rows}
    assert set(observed) == set(EXPECTED_SCHEMES)

    for file_name, scheme_name in EXPECTED_SCHEMES.items():
        _, db_scheme, agent_domain, elements, chunks, embeddings = observed[file_name]
        assert db_scheme == scheme_name
        assert agent_domain == "entitlement"
        assert elements > 0
        assert chunks > 0
        assert embeddings == chunks


@pytest.mark.integration
def test_entitlement_chunks_have_full_text_tokens(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FILTER (WHERE c.fts_tokens IS NULL), COUNT(*)
            FROM document_chunks c
            JOIN documents d ON d.document_id = c.document_id
            WHERE d.metadata->>'agent_domain' = 'entitlement'
            """
        )
        null_fts_count, total_count = cur.fetchone()

    assert total_count >= 7
    assert null_fts_count == 0


@pytest.mark.integration
def test_hindi_svanidhi_is_marked_as_metadata_fallback(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT e.extraction_mode, e.is_manual_review, e.flag_reason
            FROM document_elements e
            JOIN documents d ON d.document_id = e.document_id
            WHERE d.file_name = 'PM SVANidhi_Hindi.pdf'
            ORDER BY e.sequence_order
            LIMIT 1
            """
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == "metadata_fallback"
    assert row[1] is True
    assert "image_only_pdf_without_ocr_runtime" in row[2]
