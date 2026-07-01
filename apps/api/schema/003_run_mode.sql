-- How a feature should be built: 'direct' (just implement) or 'tdd' (tests first).
ALTER TABLE runs ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'direct';
