-- app/database/schemas/05_chunks_embedding_schema.sql

-- ============================================================================
-- FILE: 05_chunks_embedding_schema.sql
-- PURPOSE: Embedding storage layer for Hybrid RAG system
--
-- PIPELINE STAGE:
--   document_chunks  →  document_embeddings  →  retrieval
--
-- DESIGN GOALS:
--   - Support hybrid retrieval (dense + sparse)
--   - High performance vector search (pgvector)
--   - Idempotent embedding updates
--   - Scalable for millions of chunks
--   - Fully offline compatible
--
-- IMPORTANT NOTE:
--   chunk_id TYPE MUST MATCH document_chunks.chunk_id
--   Your system uses TEXT → we keep TEXT here (NOT UUID)
--
-- MODEL:
--   BGE-M3 (1024-dimensional dense vectors)
-- ============================================================================


-- ============================================================================
-- 1. EXTENSION: pgvector
-- ----------------------------------------------------------------------------
-- Required for vector similarity search
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- 2. TABLE: document_embeddings
-- ----------------------------------------------------------------------------
-- Stores embeddings for each chunk
--
-- RELATION:
--   document_chunks (1) → (1) document_embeddings
--
-- Each chunk has exactly one embedding row
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_embeddings (

    -- PRIMARY KEY (must match document_chunks)
    chunk_id TEXT PRIMARY KEY,

    -- Document reference (for filtering during retrieval)
    document_id INTEGER NOT NULL,

    -- ------------------------------------------------------------------------
    -- DENSE VECTOR (Semantic Search)
    -- ------------------------------------------------------------------------
    -- 1024-dimensional embedding from BGE-M3
    -- Used with cosine similarity
    embedding VECTOR(1024) NOT NULL,

    -- ------------------------------------------------------------------------
    -- SPARSE VECTOR (Keyword Matching)
    -- ------------------------------------------------------------------------
    -- JSONB format: {token_id: weight}
    -- Example: {"2023": 0.87, "5671": 0.34}
    sparse_vector JSONB NOT NULL DEFAULT '{}',

    -- ------------------------------------------------------------------------
    -- MODEL METADATA
    -- ------------------------------------------------------------------------
    embedding_model TEXT NOT NULL,

    -- Future-proofing (in case model changes)
    embedding_dim INTEGER DEFAULT 1024,

    -- Debug / analytics
    input_token_count INTEGER,

    -- Timestamp
    embedded_at TIMESTAMP DEFAULT NOW()

    -- ⚠️ NO trailing comma here
);


-- ============================================================================
-- 3. FOREIGN KEY CONSTRAINT
-- ----------------------------------------------------------------------------
-- Ensures embedding always maps to a valid chunk
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_chunk_embedding'
    ) THEN
        ALTER TABLE document_embeddings
        ADD CONSTRAINT fk_chunk_embedding
        FOREIGN KEY (chunk_id)
        REFERENCES document_chunks(chunk_id)
        ON DELETE CASCADE;
    END IF;
END$$;


-- ============================================================================
-- 4. INDEX: Dense Vector Search (CRITICAL)
-- ----------------------------------------------------------------------------
-- IVF Flat index for approximate nearest neighbor search
-- vector_cosine_ops → cosine similarity
--
-- lists parameter tuning:
--   small dataset  → 100
--   large dataset  → 1000+
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_document_embeddings_dense
ON document_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);


-- ============================================================================
-- 5. INDEX: Document Filtering
-- ----------------------------------------------------------------------------
-- Speeds up filtering by document_id
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_document_embeddings_doc_id
ON document_embeddings(document_id);


-- ============================================================================
-- 6. INDEX: Sparse Vector (OPTIONAL BUT FUTURE-USEFUL)
-- ----------------------------------------------------------------------------
-- Helps if querying JSONB sparse vectors directly
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_document_embeddings_sparse
ON document_embeddings
USING GIN (sparse_vector);


-- ============================================================================
-- 7. ANALYZE (IMPORTANT)
-- ----------------------------------------------------------------------------
-- Updates query planner statistics
-- ============================================================================
ANALYZE document_embeddings;


-- ============================================================================
-- 8. SAMPLE TEST QUERY
-- ----------------------------------------------------------------------------
-- Replace vector with actual query embedding
--
-- SELECT chunk_id, document_id
-- FROM document_embeddings
-- ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
-- LIMIT 10;
-- ============================================================================