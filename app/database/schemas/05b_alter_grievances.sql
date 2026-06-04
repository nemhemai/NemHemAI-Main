-- 05b_alter_grievances.sql
-- Add AI fields for Day 4 generation

ALTER TABLE grievances 
ADD COLUMN IF NOT EXISTS ai_draft_response TEXT,
ADD COLUMN IF NOT EXISTS urgency VARCHAR(50),
ADD COLUMN IF NOT EXISTS tone VARCHAR(50),
ADD COLUMN IF NOT EXISTS intent VARCHAR(100);
