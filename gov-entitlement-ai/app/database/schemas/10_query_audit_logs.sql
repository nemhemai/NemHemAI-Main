-- ===============================================================
-- TABLE: query_audit_logs
-- PURPOSE:
-- ---------------------------------------------------------------
-- Stores complete audit trail for every user query in the RAG system.
--
-- This enables:
--   • User activity tracking
--   • Debugging wrong answers
--   • Monitoring retrieval quality
--   • Performance analysis (latency)
--   • Government audit compliance
--
-- Each row = ONE query execution
-- ===============================================================

CREATE TABLE IF NOT EXISTS query_audit_logs (

    -- 🔹 Unique ID for each query event
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 🔐 USER INFORMATION
    -- ------------------------------------------------------------

    -- Reference to users table (source of truth)
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

    -- Snapshot of username at time of query
    username TEXT,


    -- 🔍 QUERY INFORMATION
    -- ------------------------------------------------------------

    -- Original user query
    query_text TEXT NOT NULL,


    -- 🧠 RESPONSE INFORMATION
    -- ------------------------------------------------------------

    -- Final generated answer from LLM
    response_text TEXT,

    -- Confidence level (low / medium / high)
    confidence TEXT,

    -- LLM model used (e.g. sarvam-1, llama, etc.)
    llm_model TEXT,


    -- 📚 RETRIEVAL INFORMATION
    -- ------------------------------------------------------------

    -- List of chunk_ids used for answer generation
    -- Stored as JSON array: ["chunk1", "chunk2", ...]
    retrieved_chunk_ids JSONB,

    -- List of document_ids involved
    -- Stored as JSON array: [1, 2, 3]
    retrieved_document_ids JSONB,


    -- ⚡ PERFORMANCE
    -- ------------------------------------------------------------

    -- Total time taken for query execution (in milliseconds)
    latency_ms INTEGER,


    -- 📊 STATUS TRACKING
    -- ------------------------------------------------------------

    -- success / failed
    status TEXT NOT NULL,

    -- Error message if failed
    error_message TEXT,


    -- 🕒 TIMESTAMP
    -- ------------------------------------------------------------

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================================
-- INDEXES (IMPORTANT FOR PERFORMANCE)
-- ===============================================================

-- 🔍 Fast filtering by user
CREATE INDEX IF NOT EXISTS idx_query_audit_user
ON query_audit_logs(user_id);

-- 🔍 Fast time-based queries (recent activity)
CREATE INDEX IF NOT EXISTS idx_query_audit_time
ON query_audit_logs(created_at DESC);

-- 🔍 Debugging failures
CREATE INDEX IF NOT EXISTS idx_query_audit_status
ON query_audit_logs(status);

-- 🔍 Search queries (optional but useful)
CREATE INDEX IF NOT EXISTS idx_query_audit_query_text
ON query_audit_logs USING GIN (to_tsvector('simple', query_text));