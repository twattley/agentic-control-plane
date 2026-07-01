-- Add the 'closing' state (approve -> closing -> gate+commit -> closed).
-- Idempotent: drop then re-add the state CHECK on existing databases.

ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_state_check;
ALTER TABLE runs ADD CONSTRAINT runs_state_check CHECK (state IN (
    'queued', 'building', 'awaiting_review', 'reviewing',
    'needs_work', 'fixing', 'awaiting_human', 'approved',
    'closing', 'closed', 'blocked'
));
