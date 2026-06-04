import json
import os
import time
from datetime import datetime
from collections import defaultdict
import threading
import uuid
from app.core.database import get_db_conn, release_db_conn

from annotated_types import doc


class IngestionAudit:

    def __init__(self):
        
        self._lock = threading.Lock()

        self.batch_start_time = None
        self.batch_end_time = None

        self.total_documents = 0
        self.successful_documents = 0
        self.failed_documents = 0

        self.documents = []
        self.exceptions = []

        self.language_breakdown = defaultdict(int)

        self.total_elements = 0
        self.total_tables = 0
        self.processing_times = []
        self.weak_pages = 0
        self.failed_pages = 0
        self.ocr_documents = 0
        self.docling_errors = 0

        #self.current_document = None

    # -------------------------------------------------------
    # Batch Control
    # -------------------------------------------------------

    def start_batch(self):

        self.batch_start_time = time.time()

    def finish_batch(self):

        self.batch_end_time = time.time()

    # -------------------------------------------------------
    # Document Lifecycle
    # -------------------------------------------------------

    def start_document(self, file_name):
        
        with self._lock:
            self.total_documents += 1

        doc = {
            "file": file_name,
            "start_time": time.time(),
            "status": "RUNNING"
        }

        return doc

    def finish_document(self, doc, status):

        end_time = time.time()
        duration = end_time - doc["start_time"]

        doc["processing_time_sec"] = round(duration, 2)
        doc["status"] = status
        
        if status != "SUCCESS":
                doc["failed"] = True
        
        with self._lock:
            self.processing_times.append(duration)

            if status == "SUCCESS":
                self.successful_documents += 1
            else:
                self.failed_documents += 1

            self.documents.append(doc)
        
    # -------------------------------------------------------
    # Metrics Recording
    # -------------------------------------------------------

    def record_validation_metrics(self, doc, validation_report):

        element_metrics = validation_report["element_metrics"]
        structure_metrics = validation_report["structure_metrics"]
        artifact_metrics = validation_report["artifact_metrics"]
        language_metrics = validation_report["language_metrics"]

        elements = element_metrics["total_elements"]
        tables = structure_metrics["tables"]
        with self._lock:
            self.total_elements += elements
            self.total_tables += tables

            for lang, count in language_metrics.items():
                self.language_breakdown[lang] += count

        # ✅ attach to doc
        doc["elements"] = elements
        doc["tables"] = tables
        doc["sections"] = structure_metrics["sections"]
        doc["headings"] = structure_metrics["headings"]
        doc["avg_tokens"] = element_metrics["avg_tokens"]
        doc["artifact_ratio"] = artifact_metrics["artifact_ratio"]
        doc["languages"] = language_metrics
        
    # -------------------------------------------------------
    # Extraction Stats Recording
    # -------------------------------------------------------
    
    def record_extraction_stats(self, doc, stats):

        weak_pages = stats.get("weak_pages", 0)
        failed_pages = stats.get("failed_pages", 0)
        docling_errors = stats.get("docling_errors", 0)
        ocr_used = stats.get("ocr_used", False)
        pages_processed = stats.get("pages_processed", 0)
        failed_details = stats.get("failed_details", [])
        with self._lock:
            self.weak_pages += weak_pages
            self.failed_pages += failed_pages
            self.docling_errors += docling_errors

            if ocr_used:
                self.ocr_documents += 1

        # ✅ attach to this specific document
        doc["pages_processed"] = pages_processed
        doc["weak_pages"] = weak_pages
        doc["failed_pages"] = failed_pages
        doc["docling_errors"] = docling_errors
        doc["ocr_used"] = ocr_used
        doc["failed_page_details"] = failed_details

    # -------------------------------------------------------
    # Exception Handling
    # -------------------------------------------------------

    def record_exception(self, doc, stage, error_message):

        recommendation = self._recommend_action(stage, error_message)

        exception_entry = {
            "file": doc["file"],
            "stage": stage,
            "error": str(error_message),
            "recommended_action": recommendation
        }
        
        with self._lock:
            self.exceptions.append(exception_entry)

        # ✅ also attach to document
        if "errors" not in doc:
            doc["errors"] = []

        doc["errors"].append(exception_entry)
        
    def _recommend_action(self, stage, error):

            error = str(error).lower()

            if stage == "registration":
                if "duplicate" in error:
                    return "Document already ingested. Verify checksum logic."

            if stage == "extraction":

                if "docling" in error:
                    return "Docling conversion failed. Check PDF integrity."

                if "ocr" in error:
                    return "OCR failure. Verify scanned document quality."

                return "Extraction failed. Inspect PDF structure."

            if stage == "validation":

                if "artifact" in error:
                    return "High artifact ratio. Improve OCR preprocessing."

                if "elements" in error:
                    return "Low element count. Verify document extraction."

                return "Validation failure. Inspect structure detection."

            return "Manual inspection required."

    
    # -------------------------------------------------------
    # Report Generation
    # -------------------------------------------------------

    def generate_report(self):

        with self._lock:
            batch_duration = self.batch_end_time - self.batch_start_time

            avg_processing_time = 0
            if self.processing_times:
                avg_processing_time = sum(self.processing_times) / len(self.processing_times)

            avg_elements = 0
            if self.total_documents:
                avg_elements = self.total_elements / self.total_documents

            success_rate = 0
            if self.total_documents:
                success_rate = (self.successful_documents / self.total_documents) * 100

            return {

                "batch_summary": {
                    "total_documents": self.total_documents,
                    "successful_documents": self.successful_documents,
                    "failed_documents": self.failed_documents,
                    "success_rate": round(success_rate, 2),
                    "batch_processing_time_sec": round(batch_duration, 2),
                    "avg_processing_time_sec": round(avg_processing_time, 2)
                },

                "language_breakdown": dict(self.language_breakdown),

                "structural_metrics": {
                    "total_elements": self.total_elements,
                    "total_tables": self.total_tables,
                    "avg_elements_per_doc": round(avg_elements, 2)
                },

                "documents": self.documents,

                "exceptions": self.exceptions,
                
                "extraction_diagnostics": {
                "weak_pages": self.weak_pages,
                "failed_pages": self.failed_pages,
                "ocr_documents": self.ocr_documents,
                "docling_errors": self.docling_errors
                }
            }

    # -------------------------------------------------------
    # Write JSON
    # -------------------------------------------------------
    
    def save_validation_debug(self, document_id, debug_report):

        output_dir = "logs/validation_debug"

        try:
            # Ensure directory exists
            os.makedirs(output_dir, exist_ok=True)

            output_path = os.path.join(output_dir, f"{document_id}.json")

            # Only store safe minimal structure
            safe_report = {
                "document_id": debug_report.get("document_id"),
                "pages": debug_report.get("pages", {})
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(safe_report, f, indent=2, ensure_ascii=False)

            print(f"Debug saved at: {output_path}")

        except Exception as e:
            print(f"ERROR saving validation debug: {str(e)}")
            
    def write_report(self):

        report = self.generate_report()

        os.makedirs("logs/ingestion_audit", exist_ok=True)

        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

        file_path = f"logs/ingestion_audit/ingestion_audit_{timestamp}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        print(f"\nAudit report written to: {file_path}")
        
        
    # Save Extracted Elements for Debugging
            
    def save_extracted_elements(self, document_id, file_path, elements, extraction_stats):
        """
        Save extracted elements to JSON file (per PDF).
        """

        try:
            output_dir = "logs/extracted_elements"
            os.makedirs(output_dir, exist_ok=True)

            file_name = os.path.basename(file_path).replace(".pdf", ".json")

            output_path = os.path.join(output_dir, file_name)

            data = {
                "document_id": document_id,
                "file_name": os.path.basename(file_path),
                "extraction_stats": extraction_stats,
                "total_elements": len(elements),
                "elements": elements
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Saved extracted elements → {output_path}")

            return output_path

        except Exception as e:
            print(f"Error saving elements: {str(e)}")
            return None
        

def log_ingestion_event(data: dict):
    """
    DB-level audit logging (persistent).

    This is separate from in-memory monitoring.
    """

    conn = None

    try:
        conn = get_db_conn()

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ingestion_audit_logs (
                    audit_id,
                    job_id,
                    document_id,
                    user_id,
                    username,
                    action,
                    stage,
                    status,
                    message,
                    error_code
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(uuid.uuid4()),
                    data.get("job_id"),
                    data.get("document_id"),
                    data.get("user_id"),
                    data.get("username"),
                    data.get("action"),
                    data.get("stage"),
                    data.get("status"),
                    data.get("message"),
                    data.get("error_code"),
                )
            )

        conn.commit()

    except Exception as e:
        print(f"Audit DB logging failed: {str(e)}")

    finally:
        if conn:
            release_db_conn(conn)