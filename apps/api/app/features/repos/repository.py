import asyncpg

from app.features.repos.models import Repo, RepoIn


async def upsert_repo(pool: asyncpg.Pool, data: RepoIn) -> Repo:
    """Register a repo, or update name/path if the slug already exists."""
    row = await pool.fetchrow(
        """
        INSERT INTO repos (slug, name, path)
        VALUES ($1, $2, $3)
        ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, path = EXCLUDED.path
        RETURNING id, slug, name, path, created_at
        """,
        data.slug, data.name, data.path,
    )
    return Repo(**dict(row))


async def get_repo(pool: asyncpg.Pool, repo_id: int) -> Repo | None:
    row = await pool.fetchrow(
        "SELECT id, slug, name, path, created_at FROM repos WHERE id = $1", repo_id
    )
    return Repo(**dict(row)) if row else None


async def list_repos(pool: asyncpg.Pool) -> list[Repo]:
    rows = await pool.fetch(
        "SELECT id, slug, name, path, created_at FROM repos ORDER BY id"
    )
    return [Repo(**dict(r)) for r in rows]
