# app/chunking/pipeline_runner.py

from typing import Any
import logging
from app.chunking.fetch_elements import load_elements_from_db
from app.chunking.insert_chunks import  insert_chunks
from app.chunking.core.structure_chunker import DocumentChunker


logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE RUNNER
# ──────────────────────────────────────────────────────────────────────────────
def run_chunking_pipeline(
    conn:        Any,
    document_id: int,
    save_to_db:  bool = True,
) -> list[dict]:
    """
    Full chunking pipeline for one document:
      1. Load elements from DB
      2. Chunk them
      3. Optionally save chunks to DB

    Args:
        conn:        psycopg2 database connection
        document_id: ID of the document to chunk
        save_to_db:  If True, inserts chunks into document_chunks table

    Returns:
        List of chunk dicts (regardless of save_to_db)
    """
    logger.info(f"Starting chunking pipeline for document_id={document_id}")

    elements = load_elements_from_db(conn, document_id)

    if not elements:
        logger.warning(f"No elements found for document_id={document_id}")
        return []

    logger.info(f"Loaded {len(elements)} elements for document_id={document_id}")

    chunker = DocumentChunker()
    chunks  = chunker.chunk(elements, document_id=document_id)

    logger.info(f"Produced {len(chunks)} chunks for document_id={document_id}")

    if save_to_db:
        insert_chunks(conn, chunks)

    return chunks
