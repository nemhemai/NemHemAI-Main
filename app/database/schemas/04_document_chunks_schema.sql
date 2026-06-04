-- app/database/schemas/04_document_chunks_schema.sql

-- =============================================================================
-- TABLE: document_chunks
-- =============================================================================
-- Purpose:
-- Stores semantically meaningful chunks derived from document_elements.
-- Each chunk is used for embedding + retrieval in RAG.
--
-- Key Design Principles:
-- - Chunk = derived layer (not source of truth)
-- - Must be reproducible from document_elements
-- - Rich metadata for explainability + debugging
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (

    -- -------------------------------------------------------------------------
    -- PRIMARY IDENTIFIERS
    -- -------------------------------------------------------------------------

    chunk_id TEXT PRIMARY KEY,
    -- Format: <document_id>_cXXXX (e.g., 12_c0001)
    -- Deterministic + human-readable

    document_id INTEGER NOT NULL,
    -- Foreign key to document_registry (logical, not enforced here)

    -- -------------------------------------------------------------------------
    -- CORE CONTENT
    -- -------------------------------------------------------------------------

    text TEXT NOT NULL,
    -- Final chunk text WITH context prefix
    -- Used for embeddings + retrieval

    text_raw TEXT,
    -- Raw concatenated content WITHOUT prefix
    -- Useful for debugging / reprocessing

    table_markdown TEXT,
    -- If chunk is table → markdown representation
    -- NULL for normal text chunks

    -- -------------------------------------------------------------------------
    -- STRUCTURAL CONTEXT
    -- -------------------------------------------------------------------------

    section_path TEXT,
    -- e.g., "5.1", "2", "3.4.2"
    -- Used for hierarchical filtering

    breadcrumb JSONB,
    -- e.g., ["Chapter 2", "Definitions"]
    -- Helps reconstruct document structure

    chunk_heading TEXT,
    -- Short heading/title associated with chunk
    -- Used in context prefix + UI display

    -- -------------------------------------------------------------------------
    -- TRACEABILITY (VERY IMPORTANT)
    -- -------------------------------------------------------------------------

    element_ids JSONB,
    -- List of element_ids used to build this chunk
    -- Enables:
    --   - trace back to source
    --   - debugging
    --   - audit

    page_range JSONB,
    -- e.g., [1,2,3]
    -- Pages covered by chunk

    sequence_range JSONB,
    -- e.g., [10, 25]
    -- Sequence order span in document

    element_types JSONB,
    -- e.g., ["paragraph", "list", "table"]
    -- Helps filtering and analysis

    -- -------------------------------------------------------------------------
    -- CHUNK TYPE
    -- -------------------------------------------------------------------------

    is_table BOOLEAN DEFAULT FALSE,
    -- True if chunk represents a table

    chunk_type TEXT,
    -- Possible values:
    --   text
    --   table
    --   heading_text
    -- Future: definition, clause, etc.

    -- -------------------------------------------------------------------------
    -- TOKEN + LANGUAGE
    -- -------------------------------------------------------------------------

    token_count INTEGER,
    -- Approx token count (important for embeddings)

    detected_language TEXT,
    -- e.g., "en", "hi", "mr"

    -- -------------------------------------------------------------------------
    -- QUALITY SIGNALS (CRITICAL FOR FILTERING)
    -- -------------------------------------------------------------------------

    min_quality_score FLOAT,
    -- Minimum quality among elements

    avg_quality_score FLOAT,
    -- Average quality score

    has_low_quality BOOLEAN,
    -- True if any element < threshold

    -- -------------------------------------------------------------------------
    -- OVERLAP TRACKING
    -- -------------------------------------------------------------------------

    has_overlap BOOLEAN DEFAULT FALSE,
    -- Indicates if chunk includes overlap from previous chunk

    overlap_tokens INTEGER DEFAULT 0,
    -- Number of tokens carried over

    -- -------------------------------------------------------------------------
    -- TIMESTAMPS
    -- -------------------------------------------------------------------------

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


-- =============================================================================
-- INDEXES (IMPORTANT FOR PERFORMANCE)
-- =============================================================================

-- Fast lookup by document
CREATE INDEX IF NOT EXISTS idx_chunks_document_id
ON document_chunks(document_id);

-- Useful for retrieval filtering
CREATE INDEX IF NOT EXISTS idx_chunks_section_path
ON document_chunks(section_path);

-- Language filtering
CREATE INDEX IF NOT EXISTS idx_chunks_language
ON document_chunks(detected_language);

-- Quality filtering
CREATE INDEX IF NOT EXISTS idx_chunks_quality
ON document_chunks(avg_quality_score);

-- GIN index for JSONB (fast search)
CREATE INDEX IF NOT EXISTS idx_chunks_element_ids_gin
ON document_chunks USING GIN (element_ids);

CREATE INDEX IF NOT EXISTS idx_chunks_breadcrumb_gin
ON document_chunks USING GIN (breadcrumb);








-- Updated by bhagirath
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS fts_tokens tsvector;

-- 2. Rebuild tokens using ENGLISH config
UPDATE document_chunks
SET fts_tokens =
    setweight(
        to_tsvector('english', coalesce(chunk_heading,'')),
        'A'
    ) ||
    setweight(
        to_tsvector('english', coalesce(section_path,'')),
        'B'
    ) ||
    setweight(
        to_tsvector('english', coalesce(text,'')),
        'C'
    );

CREATE INDEX IF NOT EXISTS idx_chunks_fts
ON document_chunks
USING GIN (fts_tokens);