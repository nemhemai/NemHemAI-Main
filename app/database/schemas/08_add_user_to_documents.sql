-- ===============================================================
-- MIGRATION: LINK DOCUMENTS WITH USERS (HYBRID DESIGN)
-- PURPOSE
-- ---------------------------------------------------------------
-- Adds:
--   • user_id (FK → users table) → source of truth
--   • uploaded_by (username snapshot) → display & audit
--
-- WHY BOTH?
-- ---------------------------------------------------------------
-- user_id:
--   • ensures referential integrity
--   • supports joins and RBAC
--
-- uploaded_by:
--   • stores username at upload time
--   • avoids extra joins for UI
--   • preserves history if username changes
-- ===============================================================


-- 🔹 Add user_id (primary identity link)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS user_id UUID;


-- 🔹 Add username snapshot
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS uploaded_by TEXT;


-- 🔹 Add foreign key constraint (only once)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_documents_user'
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT fk_documents_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE SET NULL;
    END IF;
END$$;