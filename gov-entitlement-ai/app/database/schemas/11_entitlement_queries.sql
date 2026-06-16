-- app/database/schemas/11_entitlement_queries.sql

-- =============================================================================
-- TABLE: entitlement_queries
-- Purpose:
-- Stores the complete lifecycle of citizen entitlement checks.
--
-- This includes:
--   - Raw user input query
--   - Parsed citizen profile attributes (Pydantic parsed)
--   - Neo4j / RAG matched schemes
--   - Final generated determinations (verdict, matched/unmatched criteria, citations, missing docs)
-- =============================================================================

CREATE TABLE IF NOT EXISTS entitlement_queries (
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Optional reference to the user who requested the check
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    -- Descriptive ID of the citizen (can be Aadhaar hash, name, or system UUID)
    citizen_id TEXT,
    
    -- Raw input text query describing the citizen's situation
    raw_query TEXT NOT NULL,
    
    -- Extracted profile attributes (Pydantic model serialized to JSONB)
    extracted_profile JSONB,
    
    -- Primary and adjacent scheme matches (JSONB list)
    scheme_matches JSONB,
    
    -- Final structured determination (verdict, met criteria, citations, missing docs, portals)
    determination JSONB,
    
    -- Status tracking: PENDING, PROCESSING, COMPLETED, FAILED
    status TEXT NOT NULL DEFAULT 'PENDING',
    
    -- Error message if processing failed
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_entitlement_queries_user ON entitlement_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_entitlement_queries_citizen ON entitlement_queries(citizen_id);
CREATE INDEX IF NOT EXISTS idx_entitlement_queries_status ON entitlement_queries(status);
CREATE INDEX IF NOT EXISTS idx_entitlement_queries_created ON entitlement_queries(created_at DESC);
