import json

import asyncpg

from app.features.runs.models import (
    Artifact,
    ArtifactIn,
    Event,
    EventIn,
    Lease,
    Run,
    RunIn,
)

# asyncpg returns jsonb as a raw string; decode/encode at this boundary.


async def create_run(conn: asyncpg.Connection, data: RunIn) -> Run:
    row = await conn.fetchrow(
        """
        INSERT INTO runs (repo_id, ticket_id, title)
        VALUES ($1, $2, $3)
        RETURNING id, repo_id, ticket_id, title, state, created_at, updated_at
        """,
        data.repo_id, data.ticket_id, data.title,
    )
    return Run(**dict(row))


async def get_run(conn: asyncpg.Connection, run_id: int) -> Run | None:
    row = await conn.fetchrow(
        """
        SELECT id, repo_id, ticket_id, title, state, created_at, updated_at
        FROM runs WHERE id = $1
        """,
        run_id,
    )
    return Run(**dict(row)) if row else None


async def list_runs(conn: asyncpg.Connection) -> list[Run]:
    rows = await conn.fetch(
        """
        SELECT id, repo_id, ticket_id, title, state, created_at, updated_at
        FROM runs ORDER BY id DESC
        """
    )
    return [Run(**dict(r)) for r in rows]


async def runs_in_states(conn: asyncpg.Connection, states: list[str]) -> list[Run]:
    rows = await conn.fetch(
        """
        SELECT id, repo_id, ticket_id, title, state, created_at, updated_at
        FROM runs WHERE state = ANY($1::text[]) ORDER BY updated_at
        """,
        states,
    )
    return [Run(**dict(r)) for r in rows]


async def set_state(conn: asyncpg.Connection, run_id: int, state: str) -> None:
    await conn.execute(
        "UPDATE runs SET state = $2, updated_at = now() WHERE id = $1",
        run_id, state,
    )


async def append_event(conn: asyncpg.Connection, run_id: int, data: EventIn) -> Event:
    row = await conn.fetchrow(
        """
        INSERT INTO events (run_id, type, actor, payload)
        VALUES ($1, $2, $3, $4)
        RETURNING id, run_id, type, actor, payload, created_at
        """,
        run_id, data.type, data.actor, json.dumps(data.payload),
    )
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return Event(**d)


async def list_events(conn: asyncpg.Connection, run_id: int) -> list[Event]:
    rows = await conn.fetch(
        "SELECT id, run_id, type, actor, payload, created_at"
        " FROM events WHERE run_id = $1 ORDER BY id",
        run_id,
    )
    out = []
    for r in rows:
        d = dict(r)
        d["payload"] = json.loads(d["payload"])
        out.append(Event(**d))
    return out


async def add_artifact(conn: asyncpg.Connection, run_id: int, data: ArtifactIn) -> Artifact:
    row = await conn.fetchrow(
        """
        INSERT INTO artifacts (run_id, kind, content)
        VALUES ($1, $2, $3)
        RETURNING id, run_id, kind, content, created_at
        """,
        run_id, data.kind, data.content,
    )
    return Artifact(**dict(row))


async def list_artifacts(conn: asyncpg.Connection, run_id: int) -> list[Artifact]:
    rows = await conn.fetch(
        "SELECT id, run_id, kind, content, created_at FROM artifacts WHERE run_id = $1 ORDER BY id",
        run_id,
    )
    return [Artifact(**dict(r)) for r in rows]


async def acquire_lease(conn: asyncpg.Connection, run_id: int, role: str, holder: str) -> Lease:
    row = await conn.fetchrow(
        """
        INSERT INTO leases (run_id, role, holder)
        VALUES ($1, $2, $3)
        RETURNING id, run_id, role, holder, acquired_at, released_at
        """,
        run_id, role, holder,
    )
    return Lease(**dict(row))


async def release_lease(conn: asyncpg.Connection, run_id: int, role: str) -> None:
    """Release the active lease for a role, if one is held (idempotent)."""
    await conn.execute(
        "UPDATE leases SET released_at = now()"
        " WHERE run_id = $1 AND role = $2 AND released_at IS NULL",
        run_id, role,
    )


async def list_leases(conn: asyncpg.Connection, run_id: int) -> list[Lease]:
    rows = await conn.fetch(
        "SELECT id, run_id, role, holder, acquired_at, released_at"
        " FROM leases WHERE run_id = $1 ORDER BY id",
        run_id,
    )
    return [Lease(**dict(r)) for r in rows]


async def add_decision(
    conn: asyncpg.Connection, run_id: int, decision: str, note: str | None, actor: str
) -> None:
    await conn.execute(
        "INSERT INTO decisions (run_id, decision, note, actor) VALUES ($1, $2, $3, $4)",
        run_id, decision, note, actor,
    )
