import asyncpg

from app.features.repos.models import Repo, RepoIn

_COLUMNS = "id, slug, name, path, close_gate_command, created_at"


async def upsert_repo(pool: asyncpg.Pool, data: RepoIn) -> Repo:
    """Register a repo, or update name/path if the slug already exists. A gate
    in the payload replaces the stored one; no gate leaves it alone — clearing
    is `set_close_gate`'s job, so a bare re-register can't silently ungate."""
    row = await pool.fetchrow(
        """
        INSERT INTO repos (slug, name, path, close_gate_command)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            path = EXCLUDED.path,
            close_gate_command = COALESCE(
                EXCLUDED.close_gate_command, repos.close_gate_command)
        RETURNING """ + _COLUMNS,
        data.slug, data.name, data.path, data.close_gate_command,
    )
    return Repo(**dict(row))


async def sync_repos(pool: asyncpg.Pool, projects: list[RepoIn]) -> None:
    """Register any not-yet-known project. An existing slug tracks the folder if
    it moved; its name upgrades to the pretty default only if it was never
    customised (i.e. still equals the slug) — real customisations are kept.
    The gate is set only at first registration: a rescan re-suggesting it would
    overwrite a human who cleared or customised it."""
    for p in projects:
        await pool.execute(
            """
            INSERT INTO repos (slug, name, path, close_gate_command)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (slug) DO UPDATE SET
                path = EXCLUDED.path,
                name = CASE WHEN repos.name = repos.slug
                            THEN EXCLUDED.name ELSE repos.name END
            """,
            p.slug, p.name, p.path, p.close_gate_command,
        )


async def set_close_gate(pool: asyncpg.Pool, repo_id: int, command: str | None) -> Repo | None:
    row = await pool.fetchrow(
        f"UPDATE repos SET close_gate_command = $2 WHERE id = $1 RETURNING {_COLUMNS}",
        repo_id, command,
    )
    return Repo(**dict(row)) if row else None


async def get_repo(pool: asyncpg.Pool, repo_id: int) -> Repo | None:
    row = await pool.fetchrow(
        f"SELECT {_COLUMNS} FROM repos WHERE id = $1", repo_id
    )
    return Repo(**dict(row)) if row else None


async def list_repos(pool: asyncpg.Pool) -> list[Repo]:
    rows = await pool.fetch(f"SELECT {_COLUMNS} FROM repos ORDER BY id")
    return [Repo(**dict(r)) for r in rows]
