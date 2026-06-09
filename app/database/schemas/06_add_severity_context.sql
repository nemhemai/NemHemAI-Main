-- 06_add_severity_context.sql
ALTER TABLE grievances 
ADD COLUMN IF NOT EXISTS severity_score INTEGER,
ADD COLUMN IF NOT EXISTS retrieved_context JSONB;
