# app/retrieval/hydration.py

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CHUNK HYDRATION
# ──────────────────────────────────────────────────────────────────────────────

def hydrate_chunks(
    conn:      Any,
    chunk_ids: list[str],
) -> dict[str, dict]:
    """
    Load full chunk metadata for a list of chunk_ids.
    Used after RRF to fetch complete records for the reranked candidates.
    """
    if not chunk_ids:
        return {}

    placeholders = ",".join(["%s"] * len(chunk_ids))

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
            c.has_low_quality,
            e.sparse_vector,
            d.title as document_name,
            d.file_name
        FROM document_chunks c
        LEFT JOIN document_embeddings e USING (chunk_id)
        LEFT JOIN documents d ON c.document_id = d.document_id
        WHERE c.chunk_id IN ({placeholders})
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql, chunk_ids)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            result =  {row[0]: dict(zip(cols, row)) for row in rows}
            
            # ✅ CORRECT DEBUG POSITION
            if result:
                print("HYDRATED CHUNK SAMPLE:", list(result.values())[0])

            return result

    except Exception as exc:
        logger.error(f"Chunk hydration failed: {exc}")
        return {}

