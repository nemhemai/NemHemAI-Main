-- 07_add_official_response.sql
ALTER TABLE grievances
ADD COLUMN IF NOT EXISTS official_response TEXT;
