# app/ocr_v2/experiments/fetch_extracted_elements.py

from app.core.database import get_db_conn, release_db_conn


def fetch_elements_by_document_ids(document_ids):
    """
    Fetch extracted elements for selected Gujarati documents
    from document_elements table for OCR_V2 experimentation.
    """

    if not document_ids:
        print("⚠️ No document IDs provided")
        return []

    conn = get_db_conn()

    try:
        with conn.cursor() as cur:

            placeholders = ",".join(["%s"] * len(document_ids))

            query = f"""
                SELECT
                    element_id,
                    document_id,
                    page_number,
                    element_type,
                    content_original,
                    detected_language,
                    ocr_confidence,
                    quality_score,
                    sequence_order
                FROM document_elements
                WHERE document_id IN ({placeholders})
                  AND content_original IS NOT NULL
                  AND LENGTH(TRIM(content_original)) > 0
                ORDER BY document_id, sequence_order
            """

            cur.execute(query, tuple(document_ids))

            rows = cur.fetchall()

            elements = []

            for row in rows:
                elements.append({
                    "element_id": row[0],
                    "document_id": row[1],
                    "page": row[2],
                    "element_type": row[3],
                    "raw_text": row[4],
                    "language": row[5],
                    "ocr_confidence": row[6],
                    "quality_score": row[7],
                    "sequence_order": row[8],
                })

            print(f"✅ Fetched {len(elements)} elements")

            return elements

    except Exception as e:
        print(f"❌ Error fetching elements: {e}")
        return []

    finally:
        release_db_conn(conn)