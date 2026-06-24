-- app/database/schemas/02_document_registry_schema.sql

-- ===============================================================
-- TABLE: documents
-- PURPOSE
-- ---------------------------------------------------------------
-- This table acts as the central registry for every document
-- ingested into the system.
--
-- It stores:
--   • file metadata
--   • government origin metadata
--   • document classification
--   • language information
--   • ingestion tracking
--
-- The actual document structure and text content will be stored
-- separately in the document_elements table.
--
-- This separation ensures:
--   • scalable document processing
--   • efficient retrieval
--   • clean architecture for RAG systems
--
-- This schema is designed to be universally usable by
-- government bodies at central, state, and municipal levels.
--
-- IMPORTANT DESIGN PRINCIPLES
-- ---------------------------------------------------------------
-- 1. Every physical document file appears only once.
-- 2. Duplicate ingestion is prevented using a SHA256 checksum.
-- 3. The table contains only metadata, not document content.
-- 4. Document structure and text are stored in document_elements.
-- 5. The schema is designed to support hybrid RAG pipelines.
-- ===============================================================


CREATE TABLE IF NOT EXISTS documents (

    -- ===========================================================
    -- PRIMARY IDENTIFIER
    -- ===========================================================
    -- Unique system identifier for each document.
    -- BIGSERIAL automatically generates incrementing IDs.
    -- ===========================================================

    document_id BIGSERIAL PRIMARY KEY,


    -- ===========================================================
    -- FILE METADATA
    -- ===========================================================

    -- Original uploaded file name
    file_name TEXT NOT NULL,

    -- SHA256 checksum used to prevent duplicate uploads
    -- Two identical files will produce the same checksum.
    -- This allows the ingestion pipeline to detect duplicates.
    file_checksum TEXT UNIQUE NOT NULL,

    -- File size in bytes
    file_size BIGINT,

    -- File format
    -- Allowed formats are restricted using a CHECK constraint
    file_type VARCHAR(10),

    -- Optional storage path if files are stored locally
    -- Useful when the system stores PDFs on disk.
    storage_path TEXT,

    -- URL if document was scraped or downloaded from a portal
    source_url TEXT,


    -- ===========================================================
    -- DOCUMENT IDENTIFICATION
    -- ===========================================================

    -- Official title of the document
    title TEXT,

    -- Government document reference number
    -- Example:
    --   "GR No. 145/2024"
    --   "SWM Rules 2016"
    document_number TEXT,


    -- ===========================================================
    -- GOVERNMENT METADATA
    -- ===========================================================

    -- Issuing authority
    -- Example: "Ministry of Environment and Forests"
    issuing_authority TEXT NOT NULL,

    -- Optional department short code
    -- Example: MEITY, MOF, RBI
    department_code TEXT,

    -- Level of government jurisdiction
    -- Possible values enforced via CHECK constraint
    --   central
    --   state
    --   municipal
    jurisdiction TEXT NOT NULL,

    -- Country name (default India)
    country TEXT DEFAULT 'India',

    -- State origin if applicable
    -- Example: Maharashtra, Gujarat, Delhi
    state_origin TEXT,

    -- Classification of the document
    -- Example types enforced via CHECK constraint
    --   act
    --   rule
    --   policy
    --   circular
    --   notification
    --   report
    --   guideline
    document_type TEXT NOT NULL,


    -- ===========================================================
    -- SECURITY CLASSIFICATION
    -- ===========================================================

    -- Defines the security level of the document
    -- Example values:
    --   public
    --   internal
    --   confidential
    security_level TEXT DEFAULT 'public',


    -- ===========================================================
    -- LANGUAGE INFORMATION
    -- ===========================================================

    -- Primary language of the document
    -- Example: en, hi, mr
    primary_language VARCHAR(10) NOT NULL,

    -- Indicates whether OCR was required
    -- Useful when documents are scanned PDFs
    is_ocr_processed BOOLEAN DEFAULT FALSE,


    -- ===========================================================
    -- VERSIONING
    -- ===========================================================

    -- Optional version label
    -- Example:
    --   v1
    --   amended_2022
    version_label TEXT,

    -- Date when the document was officially published
    publication_date DATE,

    -- Date when the document becomes legally effective
    effective_date DATE,


    -- ===========================================================
    -- INGESTION TRACKING
    -- ===========================================================

    -- Indicates how the document entered the system
    -- Examples:
    --   manual_upload
    --   web_scraper
    --   api_import
    ingestion_source TEXT DEFAULT 'manual_upload',

    -- Flexible metadata field for department-specific attributes
    -- Allows adding structured metadata without schema changes
    metadata JSONB DEFAULT '{}',


    -- ===========================================================
    -- SYSTEM TIMESTAMP
    -- ===========================================================

    -- Timestamp when the document record was created
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,


    -- ===========================================================
    -- DATA VALIDATION CONSTRAINTS
    -- ===========================================================

    -- Restrict allowed file types
    CONSTRAINT chk_documents_filetype
    CHECK (file_type IN ('pdf', 'docx', 'xlsx', 'image') OR file_type IS NULL),

    -- Restrict jurisdiction values
    CONSTRAINT chk_documents_jurisdiction
    CHECK (jurisdiction IN ('central', 'state', 'municipal')),

    -- Restrict security levels
    CONSTRAINT chk_documents_security
    CHECK (security_level IN ('public', 'internal', 'confidential'))

    -- Restrict document types (REMOVED FOR FLEXIBILITY)
    -- CONSTRAINT chk_documents_type
    -- CHECK (
    --     document_type IN (
    --         'act',
    --         'rule',
    --         'policy',
    --         'circular',
    --         'notification',
    --         'report',
    --         'guideline',
    --         'charter',
    --         'manual',
    --         'budget',
    --         'announcement',
    --         'form'
    --     )
    -- )

);



-- ===============================================================
-- INDEXES
-- ===============================================================
--
-- These indexes improve query performance when filtering
-- documents during retrieval.
--
-- All indexes use IF NOT EXISTS so the schema can be executed
-- multiple times without causing conflicts.
-- ===============================================================


-- Prevent duplicate document ingestion
CREATE INDEX IF NOT EXISTS idx_documents_checksum
ON documents(file_checksum);


-- Filter documents by type
CREATE INDEX IF NOT EXISTS idx_documents_type
ON documents(document_type);


-- Filter documents by jurisdiction
CREATE INDEX IF NOT EXISTS idx_documents_jurisdiction
ON documents(jurisdiction);


-- Filter documents by issuing authority
CREATE INDEX IF NOT EXISTS idx_documents_authority
ON documents(issuing_authority);