# app/chunking/insert_chunks.py

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CHUNK DB INSERTER
# ──────────────────────────────────────────────────────────────────────────────

def insert_chunks(conn: Any, chunks: list[dict]) -> None:
    """
    Insert chunks into the document_chunks table.

    Run the accompanying SQL migration to create the table before calling this.
    See: 04_document_chunks_schema.sql
    """
    if not chunks:
        return

    try:
        from psycopg2.extras import execute_values, Json
    except ImportError:
        logger.error("psycopg2 not installed — cannot insert chunks into DB")
        return

    rows = []

    for c in chunks:
        rows.append((
            c["chunk_id"],
            c["document_id"],
            c["text"],
            c["text_raw"],
            c.get("table_markdown"),
            c["section_path"],
            Json(c["breadcrumb"]),
            c["chunk_heading"],
            Json(c["element_ids"]),
            Json(c["page_range"]),
            Json(c["sequence_range"]),
            Json(c["element_types"]),
            c["is_table"],
            c["chunk_type"],
            c["token_count"],
            c["detected_language"],
            c["min_quality_score"],
            c["avg_quality_score"],
            c["has_low_quality"],
            c["has_overlap"],
            c["overlap_tokens"],
            c["chunk_heading"],
            c["section_path"],
            c["text"],
        ))

    query = """
        INSERT INTO document_chunks (
            chunk_id,
            document_id,
            text,
            text_raw,
            table_markdown,
            section_path,
            breadcrumb,
            chunk_heading,
            element_ids,
            page_range,
            sequence_range,
            element_types,
            is_table,
            chunk_type,
            token_count,
            detected_language,
            min_quality_score,
            avg_quality_score,
            has_low_quality,
            has_overlap,
            overlap_tokens,
            fts_tokens
        )
        VALUES %s
        ON CONFLICT (chunk_id) DO NOTHING;
    """

    try:
        with conn.cursor() as cur:
            execute_values(
                cur,
                query,
                rows,
                template=(
                    "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"
                    "setweight(to_tsvector('english', coalesce(%s,'')), 'A') || "
                    "setweight(to_tsvector('english', coalesce(%s,'')), 'B') || "
                    "setweight(to_tsvector('english', coalesce(%s,'')), 'C'))"
                ),
            )
        conn.commit()
        logger.info(f"Inserted {len(rows)} chunks into document_chunks")
    except Exception as exc:
        conn.rollback()
        logger.error(f"Chunk DB insert failed: {exc}")
        raise
