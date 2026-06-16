# app/retrieval/dense.py


import logging
from typing import Any
import numpy as np
from app.retrieval.filters import DENSE_CANDIDATES

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DENSE SEARCH
# ──────────────────────────────────────────────────────────────────────────────

def dense_search(
    conn:        Any,
    query_vec:   np.ndarray,
    top_n:       int   = DENSE_CANDIDATES,
    document_id: int | None = None,
    filters:     dict | None = None,
) -> list[dict]:
    """
    Find top-N chunks by cosine similarity using pgvector.

    The <=> operator computes cosine distance (1 - cosine_similarity).
    We return similarity = 1 - distance for scoring.

    Args:
        query_vec:   Normalised dense query vector (1024-dim).
        document_id: If set, restrict search to this document.
        filters:     Optional dict with keys: is_table, min_quality, language.
    """
    filters = filters or {}

    # Build WHERE clause
    where_parts = ["e.embedding IS NOT NULL"]
    params:  list = [query_vec.tolist()]

    if document_id is not None:
        where_parts.append("c.document_id = %s")
        params.append(document_id)

    if "is_table" in filters:
        where_parts.append("c.is_table = %s")
        params.append(filters["is_table"])

    if "min_quality" in filters:
        where_parts.append("c.min_quality_score >= %s")
        params.append(filters["min_quality"])

    if "language" in filters:
        where_parts.append("c.detected_language = %s")
        params.append(filters["language"])

    if "section_path" in filters:
        where_parts.append("c.section_path LIKE %s")
        params.append(filters["section_path"] + "%")

    where_clause = " AND ".join(where_parts)
    params.append(top_n)

    query = f"""
        SELECT
            c.chunk_id,
            c.document_id,
            c.text,
            c.text_raw,
            c.table_markdown,
            c.section_path,
            c.breadcrumb,
            c.chunk_heading,
            c.element_ids,
            c.page_range,
            c.is_table,
            c.chunk_type,
            c.token_count,
            c.detected_language,
            c.min_quality_score,
            c.avg_quality_score,
            e.sparse_vector,
            d.file_name AS document_name,
            1 - (e.embedding <=> %s::vector) AS dense_score
        FROM document_embeddings e
        JOIN document_chunks c USING (chunk_id)
        LEFT JOIN documents d ON c.document_id = d.document_id
        WHERE {where_clause}
        ORDER BY e.embedding <=> %s::vector
        LIMIT %s
    """

    # pgvector needs the vector twice (for ORDER BY and SELECT)
    params_final = [query_vec.tolist()] + params[1:] + [query_vec.tolist(), top_n]

    # Rebuild cleanly
    where_params = []
    if document_id is not None:
        where_params.append(document_id)
    if "is_table" in filters:
        where_params.append(filters["is_table"])
    if "min_quality" in filters:
        where_params.append(filters["min_quality"])
    if "language" in filters:
        where_params.append(filters["language"])
    if "section_path" in filters:
        where_params.append(filters["section_path"] + "%")

    final_params = [query_vec.tolist()] + where_params + [query_vec.tolist(), top_n]

    try:
        with conn.cursor() as cur:
            cur.execute(query, final_params)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]

    except Exception as exc:
        logger.error(f"Dense search failed: {exc}")
        return []