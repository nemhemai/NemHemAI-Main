# Audit & Compliance Codebase Guide

This guide is designed to help your colleague reuse the existing Governance and Audit code from the `NH_RAG` repository to build out a dedicated Audit and Compliance codebase. 

Per your request, **no code in this repository has been changed**. This file simply points out all the existing, reusable audit code components and explains how they work.

## 1. Database Audit Schemas (PostgreSQL)
The foundation of the audit tracking is built on robust PostgreSQL tables that maintain an append-only, forensic-level audit trail. These are critical for government compliance.

### `app/database/schemas/09_ingestion_audit_logs.sql`
This schema creates the `ingestion_audit_logs` table. 
* **Purpose:** It tracks the exact lifecycle of every document being ingested (who uploaded it, which stage it is in, if it failed, and why).
* **Key Fields:** `audit_id`, `job_id`, `document_id`, `user_id`, `username`, `action`, `stage`, `status`, `message`, `error_code`, `created_at`.
* **Design Principles:** Append-only, event-based, user-traceable, and pipeline stage-traceable.

### `app/database/schemas/10_query_audit_logs.sql`
This schema creates the `query_audit_logs` table.
* **Purpose:** It tracks exactly what questions users are asking the system, what the LLM responded with, and what document chunks were cited as sources.
* **Key Fields:** `user_id`, `username`, `query_text`, `response_text`, `retrieved_chunk_ids`, `retrieved_document_ids`, `confidence`, `latency_ms`, `llm_model`, `status`.

## 2. Ingestion Audit Monitoring (Python)
### `app/monitoring/ingestion_audit.py`
This is the core Python module for auditing document ingestion. It contains two main mechanisms that your colleague can reuse:

1. **`class IngestionAudit` (In-Memory Batch Tracking):**
   * Tracks total documents, successes, and failures in real-time.
   * Records processing times, language breakdowns, and exact structure metrics (elements, tables, etc.).
   * Handles exception logging and recommends specific actions based on where the error occurred (e.g., "Docling conversion failed", "High artifact ratio").
   * Outputs JSON debug reports to the `logs/ingestion_audit/` directory.

2. **`log_ingestion_event(data: dict)` (Persistent Database Logging):**
   * This function connects directly to the PostgreSQL database to insert rows into the `ingestion_audit_logs` table.
   * **Reusability:** Your colleague can import and call this exact function anytime a document hits a new stage (e.g., UPLOADED, REGISTERED, EXTRACTING, COMPLETED) to maintain compliance.

## 3. Query Audit Monitoring (Python)
### `app/monitoring/query_audit.py`
This module ensures every single prompt and response is forensically tracked.

* **`log_query_event(event: Dict[str, Any])`:**
  * **Design Principle:** It is explicitly designed to be **non-blocking** and **safe** (failures in the logging function will not crash the main application).
  * It logs the user identity, the LLM model used, the latency, the confidence score, and the exact document ID chunks retrieved.
  * **Reusability:** This can be imported as a middleware or end-of-request hook in the new compliance codebase to instantly track user activity without slowing down the LLM responses.

## Next Steps for Colleague
1. Copy the SQL schemas to initialize the audit tables in the new database.
2. Import `app.monitoring.ingestion_audit` and `app.monitoring.query_audit` into the new project's pipeline.
3. Call `log_query_event()` and `log_ingestion_event()` at major state changes to maintain compliance.
