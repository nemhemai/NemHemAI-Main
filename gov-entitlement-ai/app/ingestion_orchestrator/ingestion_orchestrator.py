# app/ingestion_orchestrator/ingestion_orchestrator.py

from app.core.database import get_db_conn, release_db_conn

from app.ingestion.document_registry import register_document
from app.ingestion.element_ingestor import ElementIngestor

from app.ingestion.pdf_extractor import PDFExtractor  # match your actual import
from app.validation.extraction_validator import ExtractionValidator

from app.utils.element_id_utils import generate_element_id

from app.chunking.pipeline_runner import run_chunking_pipeline
from app.embedding.main_embedding import run_embedding_pipeline

from app.monitoring.ingestion_audit import IngestionAudit

from app.monitoring.ingestion_audit import log_ingestion_event

def update_job_status(conn, job_id, status, progress=None, error=None):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE ingestion_jobs
            SET status = %s,
                progress = COALESCE(%s, progress),
                error = %s,
                updated_at = NOW()
            WHERE job_id = %s
        """, (status, progress, error, job_id))
    conn.commit()
    
def run_full_pipeline(job_id, file_path, metadata):
    conn = get_db_conn()

    try:
        print("STEP 1: REGISTER DOCUMENT")

        document_id = register_document(file_path, metadata)

        update_job_status(conn, job_id, "REGISTERED", 10)

        print("STEP 2: EXTRACTION")
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_start",
            "stage": "EXTRACTING",
            "status": "success",
            "message": "Extraction started"
        })
        
        update_job_status(conn, job_id, "EXTRACTING", 20)

        ingestor = ElementIngestor(conn)
        audit = IngestionAudit()
        
        doc_audit = audit.start_document(file_path)

        # --------------------------------------------------
        # CHECK IF ELEMENTS ALREADY EXIST
        # --------------------------------------------------
        if ingestor.elements_exist(document_id):
            print("[WARN] Elements already exist - skipping extraction")

            # 🔥 CHUNKING START (skip path)
            log_ingestion_event({
                "job_id": str(job_id),
                "document_id": document_id,
                "user_id": str(metadata.get("user_id")),
                "username": metadata.get("uploaded_by"),
                "action": "stage_start",
                "stage": "CHUNKING",
                "status": "success",
                "message": "Chunking started (skipped extraction)"
            })

            update_job_status(conn, job_id, "CHUNKING", 70)
            run_chunking_pipeline(conn, document_id)

            # 🔥 CHUNKING SUCCESS
            log_ingestion_event({
                "job_id": str(job_id),
                "document_id": document_id,
                "user_id": str(metadata.get("user_id")),
                "username": metadata.get("uploaded_by"),
                "action": "stage_complete",
                "stage": "CHUNKED",
                "status": "success",
                "message": "Chunking completed"
            })

            update_job_status(conn, job_id, "EMBEDDING", 85)
            
            # 🔥 EMBEDDING START
            log_ingestion_event({
                "job_id": str(job_id),
                "document_id": document_id,
                "user_id": str(metadata.get("user_id")),
                "username": metadata.get("uploaded_by"),
                "action": "stage_start",
                "stage": "EMBEDDING",
                "status": "success",
                "message": "Embedding started (skipped extraction)"
            })

            run_embedding_pipeline(document_id)

            # 🔥 EMBEDDING SUCCESS
            log_ingestion_event({
                "job_id": str(job_id),
                "document_id": document_id,
                "user_id": str(metadata.get("user_id")),
                "username": metadata.get("uploaded_by"),
                "action": "stage_complete",
                "stage": "EMBEDDED",
                "status": "success",
                "message": "Embedding completed"
            })

            update_job_status(conn, job_id, "COMPLETED", 100)
            
            log_ingestion_event({
                "job_id": str(job_id),
                "document_id": document_id,
                "user_id": str(metadata.get("user_id")),
                "username": metadata.get("uploaded_by"),
                "action": "pipeline_complete",
                "stage": "COMPLETED",
                "status": "success",
                "message": "Ingestion pipeline completed (skipped extraction)"
            })
            
            return

        # --------------------------------------------------
        # EXTRACTION
        # --------------------------------------------------
        extractor = PDFExtractor()

        def progress_callback(processed, total):
            if total > 0:
                pct = 20 + int((processed / total) * 19)
                update_job_status(conn, job_id, "EXTRACTING", pct)

        lang_str = metadata.get("primary_language", "en")
        from app.utils.ocr_utils import map_primary_language_to_tess
        tess_lang = map_primary_language_to_tess(lang_str)

        elements, extraction_stats = extractor.extract_elements(
            file_path,
            lang=tess_lang,
            progress_callback=progress_callback
        )

        print(f"Extraction complete -> {len(elements)} raw elements")
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_complete",
            "stage": "EXTRACTED",
            "status": "success",
            "message": f"{len(elements)} elements extracted"
        })

        # --------------------------------------------------
        # CLEAN INVALID ELEMENTS
        # --------------------------------------------------
        clean_elements = []
        invalid_count = 0

        for idx, e in enumerate(elements):

            if not isinstance(e, dict):
                print(f"INVALID ELEMENT TYPE at {idx}: {type(e)} -> {e}")
                invalid_count += 1
                continue

            # ensure required keys exist
            if "sequence_order" not in e:
                print(f"MISSING sequence_order at {idx}: {e}")
                invalid_count += 1
                continue

            clean_elements.append(e)

        print(f"[CLEANING] Removed {invalid_count} invalid elements")

        elements = clean_elements

        if not elements:
            raise Exception("All extracted elements are invalid")

        audit.record_extraction_stats(doc_audit, extraction_stats)

        # --------------------------------------------------
        # ELEMENT ID ASSIGNMENT (CRITICAL SECTION)
        # --------------------------------------------------
        print("STEP 2B: ELEMENT ID ASSIGNMENT")

        for idx, e in enumerate(elements):

            if not isinstance(e, dict):
                raise Exception(f"Invalid element at index {idx}: {e}")

            if isinstance(e, int):
                raise Exception(f"Integer element found at index {idx}: {e}")

            if e.get("sequence_order") is None:
                raise Exception(f"Missing sequence_order at index {idx}: {e}")

            metadata_e = e.get("metadata")

            if not isinstance(metadata_e, dict):
                metadata_e = {}
                
            page_number = metadata_e.get("page_number")

            e["element_id"] = generate_element_id(
                document_id,
                page_number,
                e["sequence_order"]
            )

        # --------------------------------------------------
        # VALIDATION
        # --------------------------------------------------
        print("STEP 3: VALIDATION")

        update_job_status(conn, job_id, "VALIDATING", 40)

        validator = ExtractionValidator()

        elements, debug_report = validator.transform(
            elements,
            document_id=document_id
        )

        print("Validation complete")

        audit.save_validation_debug(document_id, debug_report)

        # --------------------------------------------------
        # STORAGE
        # --------------------------------------------------
        print("STEP 4: STORAGE")

        update_job_status(conn, job_id, "STORING_ELEMENTS", 55)

        safe_elements = []

        for e in elements:
            try:
                if not isinstance(e, dict):
                    continue

                # 🔥 FIX METADATA AGAIN (FINAL SAFETY)
                if not isinstance(e.get("metadata"), dict):
                    e["metadata"] = {}

                e["document_id"] = document_id
                
                safe_elements.append(e)

            except Exception as inner_error:
                print("ERROR IN STORAGE ELEMENT:", e)
                raise inner_error

        ingestor.insert_elements(safe_elements)

        # --------------------------------------------------
        # CHUNKING
        # --------------------------------------------------
        print("STEP 5: CHUNKING")
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_start",
            "stage": "CHUNKING",
            "status": "success",
            "message": "Chunking started"
        })

        update_job_status(conn, job_id, "CHUNKING", 70)
        run_chunking_pipeline(conn, document_id)
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_complete",
            "stage": "CHUNKED",
            "status": "success",
            "message": "Chunking completed"
        })

        # --------------------------------------------------
        # EMBEDDING
        # --------------------------------------------------
        print("STEP 6: EMBEDDING")
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_start",
            "stage": "EMBEDDING",
            "status": "success",
            "message": "Embedding started"
        })

        update_job_status(conn, job_id, "EMBEDDING", 85)
        run_embedding_pipeline(document_id)
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "stage_complete",
            "stage": "EMBEDDED",
            "status": "success",
            "message": "Embedding completed"
        })

        update_job_status(conn, job_id, "COMPLETED", 100)
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id,
            "user_id": str(metadata.get("user_id")),
            "username": metadata.get("uploaded_by"),
            "action": "pipeline_complete",
            "stage": "COMPLETED",
            "status": "success",
            "message": "Ingestion pipeline completed successfully"
        })
        
        audit.finish_document(doc_audit, "SUCCESS")

        print("PIPELINE COMPLETED SUCCESSFULLY")

    except Exception as e:
        print("PIPELINE FAILED AT:", str(e))
        
        # ✅ MARK AUDIT FAILURE (SAFE CHECK)
        if 'doc_audit' in locals():
            audit.finish_document(doc_audit, "FAILED")
        
        log_ingestion_event({
            "job_id": str(job_id),
            "document_id": document_id if 'document_id' in locals() else None,
            "user_id": str(metadata.get("user_id")) if metadata else None,
            "username": metadata.get("uploaded_by") if metadata else None,
            "action": "stage_failed",
            "stage": "PIPELINE",
            "status": "failed",
            "message": f"Pipeline failed: {str(e)}",
            "error_code": "PIPELINE_ERROR"
        })
        
        update_job_status(conn, job_id, "FAILED", error=str(e))

    finally:
        release_db_conn(conn)