-- ===============================================================
-- TABLE: ingestion_audit_logs
-- PURPOSE
-- ---------------------------------------------------------------
-- This table maintains a COMPLETE AUDIT TRAIL for document ingestion.
--
-- It records:
--   • who performed the action (user_id, username)
--   • what action occurred (upload, stage_start, stage_complete, failure)
--   • which stage of pipeline (extract, chunk, embed, etc.)
--   • status of the action (success / failed)
--   • associated document and job
--
-- This table is CRITICAL for:
--   • government compliance
--   • forensic debugging
--   • accountability tracking
--   • pipeline monitoring
--
-- DESIGN PRINCIPLES
-- ---------------------------------------------------------------
-- 1. APPEND-ONLY (never update/delete logs)
-- 2. EVENT-BASED (multiple rows per job)
-- 3. USER-TRACEABLE (who did what)
-- 4. STAGE-TRACEABLE (where pipeline failed)
-- ===============================================================


CREATE TABLE IF NOT EXISTS ingestion_audit_logs (

    -- ===========================================================
    -- PRIMARY KEY
    -- ===========================================================
    audit_id UUID PRIMARY KEY,


    -- ===========================================================
    -- JOB + DOCUMENT CONTEXT
    -- ===========================================================

    -- ingestion job reference
    job_id UUID,

    -- document reference (nullable until created)
    document_id BIGINT,


    -- ===========================================================
    -- USER CONTEXT (CRITICAL FOR AUDIT)
    -- ===========================================================

    user_id UUID,
    username TEXT,


    -- ===========================================================
    -- ACTION METADATA
    -- ===========================================================

    -- type of action
    -- examples:
    --   upload
    --   stage_start
    --   stage_complete
    --   failure
    --   retry
    action TEXT NOT NULL,


    -- pipeline stage
    -- examples:
    --   UPLOADED
    --   REGISTERED
    --   EXTRACTING
    --   CHUNKING
    --   EMBEDDING
    --   COMPLETED
    stage TEXT NOT NULL,


    -- status of event
    -- success / failed
    status TEXT NOT NULL,


    -- ===========================================================
    -- ERROR + DEBUG INFO
    -- ===========================================================

    -- human-readable message
    message TEXT,

    -- machine-readable error code
    error_code TEXT,


    -- ===========================================================
    -- TIMESTAMP
    -- ===========================================================

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP

);