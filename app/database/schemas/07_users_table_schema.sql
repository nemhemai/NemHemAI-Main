-- ===============================================================
-- TABLE: users
-- PURPOSE
-- ---------------------------------------------------------------
-- This table manages all system users who interact with the RAG
-- platform, including government officers, administrators, and
-- authorized personnel.
--
-- It stores:
--   • authentication credentials (securely hashed)
--   • role-based access control (RBAC)
--   • identity and profile information
--   • account status and lifecycle tracking
--
-- This table forms the foundation for:
--   • RBAC (Role-Based Access Control)
--   • audit logging (who performed actions)
--   • secure access to ingestion and query systems
--
-- IMPORTANT DESIGN PRINCIPLES
-- ---------------------------------------------------------------
-- 1. Passwords are NEVER stored in plain text.
-- 2. Each user has a globally unique identifier (UUID).
-- 3. Roles define system permissions (admin, officer, viewer).
-- 4. Accounts can be activated/deactivated without deletion.
-- 5. Designed for government-grade identity tracking.
-- ===============================================================


CREATE TABLE IF NOT EXISTS users (

    -- ===========================================================
    -- PRIMARY IDENTIFIER
    -- ===========================================================
    -- Unique identifier for each user.
    -- UUID ensures global uniqueness across distributed systems.
    -- ===========================================================

    user_id UUID PRIMARY KEY,


    -- ===========================================================
    -- AUTHENTICATION FIELDS
    -- ===========================================================

    -- Unique username used for login
    username TEXT UNIQUE NOT NULL,

    -- Secure hashed password (bcrypt / argon2)
    -- NEVER store plain passwords
    password_hash TEXT NOT NULL,


    -- ===========================================================
    -- ROLE-BASED ACCESS CONTROL (RBAC)
    -- ===========================================================

    -- Defines access level of the user
    -- Example roles:
    --   admin       → full system access
    --   officer     → upload + query
    --   viewer      → read-only query
    role TEXT NOT NULL,


    -- ===========================================================
    -- USER PROFILE INFORMATION
    -- ===========================================================

    -- Full name of the user
    full_name TEXT,

    -- Official email (can be government email)
    email TEXT UNIQUE,

    -- Optional department name
    -- Example: "Municipal Corporation", "MoEF"
    department TEXT,

    -- Optional designation
    -- Example: "Sanitary Inspector", "Data Officer"
    designation TEXT,


    -- ===========================================================
    -- ACCOUNT STATUS
    -- ===========================================================

    -- Indicates whether user account is active
    is_active BOOLEAN DEFAULT TRUE,

    -- Indicates if user is verified (optional future use)
    is_verified BOOLEAN DEFAULT FALSE,


    -- ===========================================================
    -- SECURITY & TRACKING
    -- ===========================================================

    -- Last login timestamp
    last_login_at TIMESTAMPTZ,

    -- IP address of last login (optional)
    last_login_ip TEXT,


    -- ===========================================================
    -- SYSTEM TIMESTAMP
    -- ===========================================================

    -- When the user account was created
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,


    -- ===========================================================
    -- DATA VALIDATION CONSTRAINTS
    -- ===========================================================

    -- Restrict allowed roles
    CONSTRAINT chk_users_role
    CHECK (role IN ('admin', 'officer', 'viewer'))

);