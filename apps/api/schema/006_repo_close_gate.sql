-- The close gate belongs to the repo, not the service (ticket acp-015).
-- NULL means the repo closes ungated — allowed, and recorded on every run
-- that does so; the service-wide setting this replaces is gone.
ALTER TABLE repos ADD COLUMN IF NOT EXISTS close_gate_command TEXT;
