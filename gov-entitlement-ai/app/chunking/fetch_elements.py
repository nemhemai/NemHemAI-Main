# app/chunking/fetch_elements.py

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# DB LOADER HELPER
# ──────────────────────────────────────────────────────────────────────────────

def load_elements_from_db(conn: Any, document_id: int) -> list[dict]:
    """
    Load all elements for a document from the document_elements table.

    Returns a list of dicts matching the shape expected by DocumentChunker.chunk().
    Maps DB column names to the element dict keys the chunker expects.
    """
    query = """
        SELECT
            element_id,
            document_id,
            element_type,
            element_depth,
            section_path,
            heading_breadcrumb,
            sequence_order,
            page_number,
            content_original,
            structured_content,
            token_count,
            detected_language,
            extraction_mode,
            ocr_confidence,
            quality_score,
            is_manual_review,
            flag_reason,
            source_location,
            is_table,
            num_rows,
            num_cols
        FROM document_elements
        WHERE document_id = %s
        ORDER BY page_number ASC, sequence_order ASC
    """

    elements = []

    try:
        with conn.cursor() as cur:
            cur.execute(query, (document_id,))
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]

            for row in rows:
                elem = dict(zip(cols, row))

                # Normalise JSONB fields (psycopg2 returns them as dicts already)
                elem["heading_breadcrumb"] = elem.get("heading_breadcrumb") or []
                elem["structured_content"] = elem.get("structured_content") or {}
                elem["source_location"]    = elem.get("source_location") or {}
                elem["flag_reason"]        = elem.get("flag_reason") or []

                # Normalise quality_score
                elem["quality_score"] = float(elem.get("quality_score") or 1.0)

                # Re-create metadata dict (the chunker reads metadata.page_number)
                elem["metadata"] = {
                    "page_number":    elem.get("page_number"),
                    "extraction_mode": elem.get("extraction_mode", "digital"),
                    "ocr_confidence":  elem.get("ocr_confidence"),
                }

                elements.append(elem)

    except Exception as exc:
        logger.error(f"Failed to load elements for document {document_id}: {exc}")

    return elements

def get_pending_document_ids(conn):
    """
    Fetch document_ids that have elements but NOT yet chunked
    """

    query = """
        SELECT DISTINCT e.document_id
        FROM document_elements e
        LEFT JOIN document_chunks c
            ON e.document_id = c.document_id
        WHERE c.document_id IS NULL
        ORDER BY e.document_id
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            return [row[0] for row in rows]

    except Exception as e:
        logger.error(f"Failed to fetch pending document_ids: {e}")
        return []