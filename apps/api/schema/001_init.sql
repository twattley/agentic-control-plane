-- Initial schema for agentic-control-plane
-- The control plane owns workflow state, locks, append-only events,
-- artifacts, and human decisions. It never executes repo commands.
-- Every statement is idempotent (IF NOT EXISTS).

-- A registered repository a run can belong to.
CREATE TABLE IF NOT EXISTS repos (
    id          BIGSERIAL PRIMARY KEY,
    slug        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    path        TEXT NOT NULL,              -- local checkout path a worker would use
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- A unit of work moving through the builder/reviewer state machine.
-- `state` is enforced in application code (app/services/state_machine.py);
-- the CHECK here is a backstop against corrupt writes.
CREATE TABLE IF NOT EXISTS runs (
    id          BIGSERIAL PRIMARY KEY,
    repo_id     BIGINT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    ticket_id   TEXT NOT NULL,              -- work unit id, e.g. ticket filename
    title       TEXT NOT NULL,
    mode        TEXT NOT NULL DEFAULT 'direct',  -- 'direct' | 'tdd' (tests first)
    state       TEXT NOT NULL DEFAULT 'queued'
                CHECK (state IN (
                    'queued', 'building', 'awaiting_review', 'reviewing',
                    'needs_work', 'fixing', 'awaiting_human', 'approved',
                    'closing', 'closed', 'blocked'
                )),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runs_state_idx ON runs (state);

-- Append-only event log. The source of truth for what happened on a run.
CREATE TABLE IF NOT EXISTS events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,
    actor       TEXT NOT NULL,              -- builder | reviewer | human | system
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS events_run_idx ON events (run_id, id);

-- Attached outputs: diffs, test output, screenshots, logs.
CREATE TABLE IF NOT EXISTS artifacts (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,              -- diff | test_output | screenshot | log
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS artifacts_run_idx ON artifacts (run_id, id);

-- Role leases. A run holds at most one active lease per role at a time.
CREATE TABLE IF NOT EXISTS leases (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,              -- builder | reviewer | human
    holder      TEXT NOT NULL,              -- who holds it, e.g. codex, claude, tom
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at TIMESTAMPTZ
);

-- one active (unreleased) lease per run+role
CREATE UNIQUE INDEX IF NOT EXISTS leases_active_role_idx
    ON leases (run_id, role) WHERE released_at IS NULL;

-- Human decisions on a run.
CREATE TABLE IF NOT EXISTS decisions (
    id          BIGSERIAL PRIMARY KEY,
    run_id      BIGINT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL,              -- approve | request_changes | block | close
    note        TEXT,
    actor       TEXT NOT NULL DEFAULT 'human',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
