# app/embedding/chunk_fetcher.py

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# DB HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def load_chunks_for_embedding(
    conn: Any,
    document_id: int,
    batch_size: int
) -> list[dict]:
    """
    Load chunks from document_chunks that have not yet been embedded.

    """
    query = """
        SELECT c.chunk_id, c.text, c.token_count, c.detected_language
        FROM document_chunks c
        LEFT JOIN document_embeddings e USING (chunk_id)
        WHERE c.document_id = %s
        AND e.chunk_id IS NULL
        ORDER BY c.token_count DESC
        LIMIT %s
        """

    try:
        with conn.cursor() as cur:
            cur.execute(query, (document_id, batch_size))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in rows]
    except Exception as exc:
        logger.error(f"Failed to load chunks for document {document_id}: {exc}")
        return []
