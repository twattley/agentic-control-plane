import asyncpg

from app.features.discussions.models import Discussion, DiscussionMessage

_COLS = "id, repo_id, session_id, state, ticket_slug, skill_name, created_at, updated_at"


async def create_discussion(
    pool: asyncpg.Pool, repo_id: int, skill_name: str | None = None
) -> Discussion:
    row = await pool.fetchrow(
        f"INSERT INTO discussions (repo_id, skill_name) VALUES ($1, $2) RETURNING {_COLS}",
        repo_id, skill_name,
    )
    return Discussion(**dict(row))


async def get_discussion(pool: asyncpg.Pool, discussion_id: int) -> Discussion | None:
    row = await pool.fetchrow(
        f"SELECT {_COLS} FROM discussions WHERE id = $1", discussion_id
    )
    return Discussion(**dict(row)) if row else None


async def delete_discussion(pool: asyncpg.Pool, discussion_id: int) -> None:
    await pool.execute("DELETE FROM discussions WHERE id = $1", discussion_id)


async def list_discussions(pool: asyncpg.Pool, repo_id: int) -> list[Discussion]:
    rows = await pool.fetch(
        f"SELECT {_COLS} FROM discussions WHERE repo_id = $1 ORDER BY updated_at DESC", repo_id
    )
    return [Discussion(**dict(r)) for r in rows]


async def set_session(pool: asyncpg.Pool, discussion_id: int, session_id: str) -> None:
    await pool.execute(
        "UPDATE discussions SET session_id = $2, updated_at = now() WHERE id = $1",
        discussion_id, session_id,
    )


async def set_frozen(pool: asyncpg.Pool, discussion_id: int, ticket_slug: str) -> None:
    await pool.execute(
        "UPDATE discussions SET state = 'frozen', ticket_slug = $2, updated_at = now()"
        " WHERE id = $1",
        discussion_id, ticket_slug,
    )


async def add_message(
    pool: asyncpg.Pool, discussion_id: int, role: str, content: str
) -> DiscussionMessage:
    row = await pool.fetchrow(
        """
        INSERT INTO discussion_messages (discussion_id, role, content)
        VALUES ($1, $2, $3)
        RETURNING id, discussion_id, role, content, created_at
        """,
        discussion_id, role, content,
    )
    return DiscussionMessage(**dict(row))


async def list_messages(pool: asyncpg.Pool, discussion_id: int) -> list[DiscussionMessage]:
    rows = await pool.fetch(
        "SELECT id, discussion_id, role, content, created_at"
        " FROM discussion_messages WHERE discussion_id = $1 ORDER BY id",
        discussion_id,
    )
    return [DiscussionMessage(**dict(r)) for r in rows]
