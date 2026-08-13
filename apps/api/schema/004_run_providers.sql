-- Per-run agent choice. A provider spec is "provider[:model]" — e.g.
-- "claude:sonnet", "codex", "stub". NULL falls back to the global
-- AGENTIC_CONTROL_PLANE_{BUILDER,REVIEWER}_PROVIDER setting.
ALTER TABLE runs ADD COLUMN IF NOT EXISTS builder_provider TEXT;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS reviewer_provider TEXT;
