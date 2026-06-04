-- app/database/schemas/03_document_elements_schema.sql

-- ===============================================================
-- TABLE: document_elements
-- ===============================================================
-- PURPOSE
-- ---------------------------------------------------------------
-- This table stores structured elements extracted from government
-- documents after passing through the extraction + validation pipeline.
--
-- Each row represents a logical unit such as:
--
--   • title
--   • heading
--   • section
--   • paragraph
--   • clause
--   • list_item
--   • table
--   • annexure
--
-- PIPELINE POSITION
-- ---------------------------------------------------------------
-- Raw PDF → Extraction → Validation (quality scoring)
--            ↓
--      document_elements  ← YOU ARE HERE
--            ↓
--      Chunking Layer
--            ↓
--      Embedding Layer
--            ↓
--      Hybrid RAG Retrieval
--
-- DESIGN PRINCIPLES
-- ---------------------------------------------------------------
-- 1. Each row = one validated element
-- 2. Preserve document structure + order
-- 3. Store validation intelligence (quality-aware RAG)
-- 4. Keep DB lean but query-efficient
-- 5. Support both OCR and digital documents
-- ===============================================================


CREATE TABLE IF NOT EXISTS document_elements (

    -- ===========================================================
    -- PRIMARY KEY
    -- ===========================================================
    -- Unique identifier for each element.
    --
    -- NOTE:
    -- This is generated during extraction (not auto-increment).
    -- Example: "1_p1_e0"
    --
    -- Format:
    --   {document_id}_p{page}_e{sequence}
    -- ===========================================================
    element_id TEXT PRIMARY KEY,


    -- ===========================================================
    -- DOCUMENT RELATIONSHIP
    -- ===========================================================
    -- Links element to parent document.
    --
    -- ON DELETE CASCADE ensures all elements are removed if
    -- the document is deleted.
    -- ===========================================================
    document_id BIGINT NOT NULL
        REFERENCES documents(document_id)
        ON DELETE CASCADE,


    -- ===========================================================
    -- HIERARCHICAL STRUCTURE (OPTIONAL / FUTURE)
    -- ===========================================================
    -- Allows building nested document structures:
    --
    -- Section → Subsection → Paragraph
    --
    -- NOTE:
    -- Currently optional (can be NULL)
    -- ===========================================================
    parent_element_id TEXT,


    -- ===========================================================
    -- ELEMENT CLASSIFICATION
    -- ===========================================================
    -- High-level classification of element.
    --
    -- Examples:
    --   heading
    --   section
    --   paragraph
    --   clause
    --   table
    -- ===========================================================
    element_type TEXT NOT NULL,


    -- Optional finer classification
    element_subtype TEXT,


    -- ===========================================================
    -- HIERARCHY INFORMATION
    -- ===========================================================
    -- Depth level in document tree
    --
    -- Example:
    --   heading → 1
    --   paragraph → 2
    -- ===========================================================
    element_depth INTEGER,


    -- Legal reference path (important for govt docs)
    --
    -- Example:
    --   1
    --   1.1
    --   1.1(a)
    -- ===========================================================
    section_path TEXT,


    -- Breadcrumb of headings (context preservation)
    --
    -- Example:
    -- ["Chapter 1", "Introduction"]
    -- ===========================================================
    heading_breadcrumb JSONB,


    -- ===========================================================
    -- DOCUMENT ORDERING
    -- ===========================================================
    -- Maintains reading order
    -- ===========================================================
    sequence_order INTEGER NOT NULL,


    -- Page number extracted from metadata
    page_number INTEGER,


    -- ===========================================================
    -- CONTENT STORAGE
    -- ===========================================================
    -- Original extracted text
    content_original TEXT,


    -- Optional cleaned text (future normalization)
    content_cleaned TEXT,


    -- Optional translated content (future multilingual support)
    content_translated TEXT,


    -- Structured content (used for tables)
    --
    -- Example:
    -- {
    --   "headers": [...],
    --   "rows": [...]
    -- }
    -- ===========================================================
    structured_content JSONB,


    -- ===========================================================
    -- SOURCE LOCATION
    -- ===========================================================
    -- Stores bounding box + page for UI highlighting
    --
    -- Example:
    -- {"page": 2, "bbox": {...}}
    -- ===========================================================
    source_location JSONB,


    -- ===========================================================
    -- NLP / PROCESSING
    -- ===========================================================
    -- Token count used in chunking
    token_count INTEGER,


    -- Language detection (en / hi / mr etc.)
    detected_language TEXT,


    -- ===========================================================
    -- EXTRACTION METADATA
    -- ===========================================================
    -- Mode used for extraction
    --
    -- digital → high quality PDF
    -- ocr     → scanned document
    -- ===========================================================
    extraction_mode TEXT,


    -- OCR confidence (if applicable)
    ocr_confidence FLOAT,


    -- ===========================================================
    -- VALIDATION LAYER (CORE FEATURE)
    -- ===========================================================
    -- Output from your ExtractionValidator
    --
    -- This is critical for:
    --   • filtering bad data
    --   • ranking retrieval results
    --   • improving RAG quality
    -- ===========================================================

    -- Quality score (0 → 1)
    quality_score FLOAT,


    -- Flag for manual review
    is_manual_review BOOLEAN,


    -- Reasons for degradation
    --
    -- Example:
    -- ["low_content", "corrupted_text"]
    flag_reason JSONB,


    -- ===========================================================
    -- TABLE-SPECIFIC FIELDS
    -- ===========================================================
    -- Helps with structured table handling
    -- ===========================================================
    is_table BOOLEAN DEFAULT FALSE,
    num_rows INTEGER,
    num_cols INTEGER,


    -- ===========================================================
    -- SYSTEM TIMESTAMPS
    -- ===========================================================
    -- When the element was inserted
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Future updates tracking
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,


    -- ===========================================================
    -- FULL TEXT SEARCH (POSTGRES)
    -- ===========================================================
    -- Enables lexical search (hybrid retrieval)
    --
    -- 'simple' dictionary avoids stemming issues for
    -- multilingual government documents
    -- ===========================================================
    fts_tokens tsvector GENERATED ALWAYS AS
        (to_tsvector('simple', COALESCE(content_original,''))) STORED
);



-- ===============================================================
-- INDEXES (PERFORMANCE OPTIMIZATION)
-- ===============================================================

-- Fast lookup by document
CREATE INDEX IF NOT EXISTS idx_elements_document
ON document_elements(document_id);


-- Maintain reading order
CREATE INDEX IF NOT EXISTS idx_elements_sequence
ON document_elements(document_id, sequence_order);


-- Page-level filtering
CREATE INDEX IF NOT EXISTS idx_elements_page
ON document_elements(document_id, page_number);


-- Filter by element type
CREATE INDEX IF NOT EXISTS idx_elements_type
ON document_elements(element_type);


-- Quality-based retrieval (VERY IMPORTANT)
CREATE INDEX IF NOT EXISTS idx_elements_quality
ON document_elements(quality_score);


-- Manual review filtering
CREATE INDEX IF NOT EXISTS idx_elements_review
ON document_elements(is_manual_review);


-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_elements_fts
ON document_elements
USING GIN (fts_tokens);


-- Fuzzy matching (OCR robustness)
CREATE INDEX IF NOT EXISTS idx_elements_trgm
ON document_elements
USING GIN (content_original gin_trgm_ops);

