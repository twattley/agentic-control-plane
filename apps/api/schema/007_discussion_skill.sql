-- The installed skill chosen when a shaping discussion starts (ticket acp-030).
-- NULL preserves the existing plain shaping conversation.
ALTER TABLE discussions ADD COLUMN IF NOT EXISTS skill_name TEXT;
