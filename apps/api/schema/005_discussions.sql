-- Ticket-shaping discussions: the strand that exists BEFORE a ticket is
-- frozen. Each agent turn is a short-lived `claude -p --resume` run in the
-- repo checkout; session_id is the CLI's conversation handle.
CREATE TABLE IF NOT EXISTS discussions (
    id           BIGSERIAL PRIMARY KEY,
    repo_id      BIGINT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    session_id   TEXT,                          -- NULL until the first agent reply
    state        TEXT NOT NULL DEFAULT 'open'
                 CHECK (state IN ('open', 'frozen')),
    ticket_slug  TEXT,                          -- set at freeze
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS discussion_messages (
    id             BIGSERIAL PRIMARY KEY,
    discussion_id  BIGINT NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    role           TEXT NOT NULL CHECK (role IN ('human', 'agent')),
    content        TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS discussions_repo_idx ON discussions (repo_id, state);
