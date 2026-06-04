# app/ingestion/element_ingestor.py

from psycopg2.extras import execute_values, Json
import json

class ElementIngestor:

    def __init__(self, conn):
        self.conn = conn
        
    def elements_exist(self, document_id):
        """
        Check if elements for this document already exist in DB.
        Used to prevent duplicate ingestion.
        """

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM document_elements WHERE document_id = %s LIMIT 1",
                    (document_id,)
                )
                return cur.fetchone() is not None

        except Exception as e:
            print(f"ERROR checking existing elements: {e}")
            return False

    def insert_elements(self, elements):

        if not elements:
            print("WARN: No elements to insert")
            return

        rows = []

        for e in elements:
            # -------------------------
            # FIX: heading_breadcrumb
            # -------------------------
            breadcrumb = e.get("heading_breadcrumb")

            # If already string → convert to list
            if isinstance(breadcrumb, str):
                try:
                    breadcrumb = json.loads(breadcrumb)
                except:
                    breadcrumb = []

            # Ensure it's always a list
            if not isinstance(breadcrumb, list):
                breadcrumb = []

            breadcrumb_json = Json(breadcrumb)
            
            # -------------------------
            # TABLE MAPPING FIX
            # -------------------------
            is_table = e.get("element_type") == "table"

            structured = e.get("structured_content") or {}

            num_rows = None
            num_cols = None

            if is_table:
                num_rows = structured.get("num_rows")
                num_cols = structured.get("num_cols")

            metadata = e.get("metadata", {}) or {}

            row = (
                e.get("element_id"),
                e.get("document_id"),
                e.get("element_type"),
                e.get("element_depth"),
                e.get("section_path"),
                breadcrumb_json,          # FIX
                e.get("sequence_order"),
                metadata.get("page_number"),
                e.get("content_original"),
                Json(e.get("structured_content") or {}),          # FIX
                e.get("token_count"),
                e.get("detected_language"),
                metadata.get("extraction_mode"),
                metadata.get("ocr_confidence"),
                e.get("quality_score"),
                e.get("is_manual_review"),
                Json(e.get("flag_reason") or []),                 # FIX
                Json(e.get("source_location") or {}),
                is_table,          # NEW
                num_rows,          # NEW
                num_cols           # NEW FIX
            )

            rows.append(row)

        query = """
        INSERT INTO document_elements (
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
        )
        VALUES %s
        ON CONFLICT (element_id) DO NOTHING;
        """

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, query, rows)

            self.conn.commit()
            print(f"Inserted {len(rows)} elements into DB")

        except Exception as e:
            self.conn.rollback()
            print(f"DB Insert Error: {str(e)}")
