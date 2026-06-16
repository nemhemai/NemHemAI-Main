# app/retrieval/sparse.py

import logging
from typing import Any

from app.retrieval.filters import SPARSE_CANDIDATES

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# SPARSE SEARCH
# ──────────────────────────────────────────────────────────────────────────────

import re

def build_or_tsquery(query: str) -> str:
    words = re.findall(r"\b\w+\b", query.lower())

    # remove stopwords (important)
    STOPWORDS = {
        "the","is","in","of","for","to","and","or",
        "on","with","by","as","at","an","be","this",
        "that","are","from","what","how","when","where"
    }

    words = [w for w in words if w not in STOPWORDS]

    # create OR query
    return " | ".join(words)

def sparse_search(
    conn:         Any,
    query:        str,
    query_sparse: dict,
    top_n:        int  = SPARSE_CANDIDATES,
    document_id:  int | None = None,
    filters:      dict | None = None,
) -> list[dict]:
    """
    Find top-N chunks using PostgreSQL full-text search.

    Two-pass approach:
      Pass 1: FTS (tsvector @@ tsquery) narrows to relevant documents — fast.
      Pass 2: Sparse dot product re-scores and reranks the FTS results.

    The FTS pass uses plainto_tsquery which handles multi-word queries
    without requiring the user to know tsquery syntax.
    """
    filters = filters or {}

    where_parts = [ """ c.fts_tokens @@ to_tsquery('english', %s) """]
    ts_query = build_or_tsquery(query)
    params: list = [ts_query]

    if document_id is not None:
        where_parts.append("c.document_id = %s")
        params.append(document_id)

    if "is_table" in filters:
        where_parts.append("c.is_table = %s")
        params.append(filters["is_table"])

    if "min_quality" in filters:
        where_parts.append("c.min_quality_score >= %s")
        params.append(filters["min_quality"])

    if "section_path" in filters:
        where_parts.append("c.section_path LIKE %s")
        params.append(filters["section_path"] + "%")

    where_parts.append("e.sparse_vector IS NOT NULL")

    where_clause = " AND ".join(where_parts)
    params.append(top_n * 3)   # fetch 3x to re-score with sparse dot product

    sql = f"""
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
            ts_rank(c.fts_tokens, websearch_to_tsquery('english', %s), 32) AS fts_score
        FROM document_chunks c
        JOIN document_embeddings e USING (chunk_id)
        LEFT JOIN documents d ON c.document_id = d.document_id
        WHERE {where_clause}
        ORDER BY fts_score DESC
        LIMIT %s
    """

    params_final = [query] + params

    try:
        with conn.cursor() as cur:
            cur.execute(sql, params_final)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            results = [dict(zip(cols, row)) for row in rows]

            # 🚨 FALLBACK: if no results, use broader query
            if not results:
                logger.warning("[SPARSE] No results → running fallback query")

                fallback_sql = f"""
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
                        ts_rank_cd(
                            c.fts_tokens,
                            plainto_tsquery('english', %s),
                            32
                        ) AS fts_score
                    FROM document_chunks c
                    JOIN document_embeddings e USING (chunk_id)
                    LEFT JOIN documents d ON c.document_id = d.document_id
                    WHERE c.fts_tokens @@ to_tsquery('english', %s)
                    ORDER BY fts_score DESC
                    LIMIT %s
                """

                cur.execute(fallback_sql, [query, query, top_n * 3])
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                results = [dict(zip(cols, row)) for row in rows]

    except Exception as exc:
        logger.error(f"Sparse search failed: {exc}")
        return []
    
    # ✅ Use PostgreSQL FTS score as sparse_score
    for r in results:
        r["sparse_score"] = r.get("fts_score", 0.0)
    
    logger.info(f"[SPARSE] Retrieved {len(results)} rows")
    if results:
        logger.info(f"[SPARSE] Top score: {results[0]['fts_score']}")

    return results[:top_n]