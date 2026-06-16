-- app/database/schemas/12_entitlement_agent_schema.sql

-- =============================================================================
-- TABLE: citizens
-- Purpose:
-- Stores registered citizen identities with unique mobile, Aadhaar and email.
-- =============================================================================
CREATE TABLE IF NOT EXISTS citizens (
    citizen_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mobile_number VARCHAR(20) NOT NULL UNIQUE,
    aadhaar_id VARCHAR(12) NOT NULL UNIQUE,
    email VARCHAR(100),
    is_verified BOOLEAN DEFAULT FALSE,
    verification_source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: citizen_profiles
-- Purpose:
-- Stores the Citizen 360 profile, family structure, and socio-economic data.
-- =============================================================================
CREATE TABLE IF NOT EXISTS citizen_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL REFERENCES citizens(citizen_id) ON DELETE CASCADE,
    personal_info JSONB DEFAULT '{}'::jsonb,
    household_info JSONB DEFAULT '{}'::jsonb,
    socio_economic_info JSONB DEFAULT '{}'::jsonb,
    existing_benefits JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: citizen_documents
-- Purpose:
-- Stores verification documents uploaded for the Verification Agent.
-- =============================================================================
CREATE TABLE IF NOT EXISTS citizen_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL REFERENCES citizens(citizen_id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    verification_status VARCHAR(20) DEFAULT 'PENDING',
    ocr_extracted_data JSONB DEFAULT '{}'::jsonb,
    anomaly_detected BOOLEAN DEFAULT FALSE,
    anomaly_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: citizen_applications
-- Purpose:
-- Stores the scheme applications submitted by a citizen, tracking live status.
-- =============================================================================
CREATE TABLE IF NOT EXISTS citizen_applications (
    application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL REFERENCES citizens(citizen_id) ON DELETE CASCADE,
    scheme_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'DRAFT',
    form_data JSONB DEFAULT '{}'::jsonb,
    tracking_status JSONB DEFAULT '{}'::jsonb,
    submission_channel VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TABLE: entitlement_audits
-- Purpose:
-- Logs compliance records and eligibility justifications for the Audit Agent.
-- =============================================================================
CREATE TABLE IF NOT EXISTS entitlement_audits (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID REFERENCES citizens(citizen_id) ON DELETE SET NULL,
    query_id UUID,
    scheme_name VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    decision_trace JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for performance
CREATE INDEX IF NOT EXISTS idx_citizens_mobile ON citizens(mobile_number);
CREATE INDEX IF NOT EXISTS idx_citizens_aadhaar ON citizens(aadhaar_id);
CREATE INDEX IF NOT EXISTS idx_citizen_profiles_citizen ON citizen_profiles(citizen_id);
CREATE INDEX IF NOT EXISTS idx_citizen_documents_citizen ON citizen_documents(citizen_id);
CREATE INDEX IF NOT EXISTS idx_citizen_applications_citizen ON citizen_applications(citizen_id);
CREATE INDEX IF NOT EXISTS idx_entitlement_audits_citizen ON entitlement_audits(citizen_id);
