from __future__ import annotations

import re
from typing import Any


HIGH_VALUE_TERMS = (
    "eligibility",
    "eligible",
    "eligibility criteria",
    "criteria",
    "beneficiary",
    "beneficiaries",
    "required document",
    "required documents",
    "income limit",
    "income criteria",
    "exclusion",
    "excluded",
    "conditions",
    "qualification conditions",
    "land ownership",
    "landholding",
    "aadhaar",
    "bank account",
    "qualification",
    "applicant",
)

LOW_VALUE_TERMS = (
    "faq",
    "frequently asked",
    "implementation",
    "administrative",
    "administration",
    "monitoring",
    "pmu",
    "coordination",
    "tendering",
    "reporting",
    "dashboard",
    "progress report",
    "review meeting",
    "annexure",
    "publicity",
    "awareness",
)


def _build_or_tsquery(query: str) -> str:
    stopwords = {
        "the", "is", "in", "of", "for", "to", "and", "or", "on", "with",
        "by", "as", "at", "an", "be", "this", "that", "are", "from",
        "what", "how", "when", "where", "can", "i", "a", "my",
    }
    terms = [
        term
        for term in re.findall(r"\b\w+\b", query.lower())
        if len(term) > 1 and term not in stopwords
    ]
    return " | ".join(terms) or "entitlement"


def _retrieval_intent(query: str) -> str:
    query = query.lower()
    intent_terms = [
        "eligibility criteria",
        "eligible beneficiary",
        "required documents",
        "income limit",
        "land ownership",
        "exclusion conditions",
        "qualification conditions",
    ]
    return f"{query} {' '.join(intent_terms)}"


def retrieve_entitlement_clauses(
    conn: Any,
    query: str,
    *,
    top_k: int = 5,
    scheme_name: str | None = None,
    scheme_category: str | None = None,
    language: str | None = "en",
) -> list[dict]:
    """
    Fast entitlement retrieval over already-ingested chunks.

    This intentionally avoids query-time BGE-M3 encoding so tests and API smoke
    checks stay quick on CPU. It uses PostgreSQL full-text search plus metadata
    filters, and returns citation-ready document/chunk fields.
    """
    if not query or not query.strip():
        return []

    ts_query = _build_or_tsquery(_retrieval_intent(query))
    where_parts = [
        "d.metadata->>'agent_domain' = 'entitlement'",
        "c.fts_tokens @@ to_tsquery('english', %s)",
    ]
    where_params: list[Any] = [ts_query]

    if scheme_name:
        where_parts.append("d.metadata->>'scheme_name' = %s")
        where_params.append(scheme_name)

    if scheme_category:
        where_parts.append("d.metadata->>'scheme_category' = %s")
        where_params.append(scheme_category)

    if language:
        where_parts.append("c.detected_language = %s")
        where_params.append(language)

    params: list[Any] = [ts_query, *where_params, top_k]

    sql = f"""
        WITH ranked AS (
        SELECT
            c.chunk_id,
            c.document_id,
            d.file_name,
            d.title,
            d.metadata->>'scheme_name' AS scheme_name,
            d.metadata->>'scheme_category' AS scheme_category,
            c.section_path,
            c.page_range,
            c.chunk_heading,
            c.text,
            c.detected_language,
            c.avg_quality_score,
            ts_rank(c.fts_tokens, to_tsquery('english', %s), 32) AS lexical_score,
            lower(coalesce(c.chunk_heading, '') || ' ' || coalesce(c.section_path, '')) AS metadata_text,
            lower(coalesce(c.text, '')) AS body_text,
            CASE
                WHEN lower(coalesce(c.chunk_heading, '') || ' ' || coalesce(c.section_path, ''))
                    SIMILAR TO '%%(eligibility|eligibility criteria|beneficiary|beneficiaries|required document|required documents|exclusions|exclusion|excluded|income limit|income criteria|land ownership|landholding|qualification conditions|conditions|eligible|criteria|aadhaar|bank account|qualification|applicant)%%'
                THEN 0.65 ELSE 0 END AS metadata_positive_boost,
            CASE
                WHEN lower(coalesce(c.text, ''))
                    SIMILAR TO '%%(eligibility|eligibility criteria|beneficiary|beneficiaries|required document|required documents|exclusions|exclusion|excluded|income limit|income criteria|land ownership|landholding|qualification conditions|conditions|eligible|criteria|aadhaar|bank account|qualification|applicant)%%'
                THEN 0.35 ELSE 0 END AS body_positive_boost,
            CASE
                WHEN lower(coalesce(c.chunk_heading, '') || ' ' || coalesce(c.section_path, '') || ' ' || coalesce(c.text, ''))
                    SIMILAR TO '%%(implementation|monitoring|administration|pmu|coordination|faq|tendering|reporting|frequently asked|administrative|dashboard|progress report|review meeting|annexure|publicity|awareness)%%'
                THEN 0.60 ELSE 0 END AS negative_penalty
        FROM document_chunks c
        JOIN documents d ON d.document_id = c.document_id
        WHERE {" AND ".join(where_parts)}
        )
        SELECT
            *,
            GREATEST(0.0001, (lexical_score + metadata_positive_boost + body_positive_boost) * (1.0 - negative_penalty)) AS score,
            metadata_positive_boost > 0 AS metadata_eligibility_signal,
            body_positive_boost > 0 AS body_eligibility_signal,
            metadata_positive_boost + body_positive_boost > 0 AS eligibility_signal,
            negative_penalty > 0 AS low_value_signal
        FROM ranked
        ORDER BY
            metadata_eligibility_signal DESC,
            eligibility_signal DESC,
            low_value_signal ASC,
            score DESC,
            avg_quality_score DESC NULLS LAST
        LIMIT %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in rows]
