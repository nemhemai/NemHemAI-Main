# app/embedding/embedding_store.py

from app.core.config import settings
import logging
logger = logging.getLogger(__name__)
from typing import Any
import numpy as np


def store_embeddings(
    conn:        Any,
    document_id: int,
    chunk_ids:   list[str],
    dense_vecs:  np.ndarray,
    sparse_vecs: list[dict],
    token_counts: list[int],
) -> None:
    """
    Bulk-insert embedding records into document_embeddings.
    Uses ON CONFLICT DO UPDATE so re-running is idempotent.
    """
    try:
        from psycopg2.extras import execute_values, Json
    except ImportError:
        raise ImportError("psycopg2 required for DB insertion")

    rows = []

    for chunk_id, dense, sparse, n_tokens in zip(
        chunk_ids, dense_vecs, sparse_vecs, token_counts
    ):
        rows.append((
            chunk_id,
            document_id,
            dense.tolist(),       # pgvector accepts Python list
            Json(sparse),
            settings.EMBED_MODEL_PATH,
            n_tokens,
        ))

    query = """
        INSERT INTO document_embeddings (
            chunk_id,
            document_id,
            embedding,
            sparse_vector,
            embedding_model,
            input_token_count
        )
        VALUES %s
        ON CONFLICT (chunk_id) DO UPDATE SET
            embedding       = EXCLUDED.embedding,
            sparse_vector   = EXCLUDED.sparse_vector,
            embedding_model = EXCLUDED.embedding_model,
            embedded_at     = NOW(),
            input_token_count = EXCLUDED.input_token_count;
    """

    try:
        with conn.cursor() as cur:
            execute_values(cur, query, rows, template="(%s,%s,%s::vector,%s,%s,%s)")
        conn.commit()
        logger.info(f"Stored {len(rows)} embeddings for document_id={document_id}")

    except Exception as exc:
        conn.rollback()
        logger.error(f"Embedding DB insert failed: {exc}")
        raise
