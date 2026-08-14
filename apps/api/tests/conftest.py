import asyncio
from pathlib import Path

import asyncpg
import pytest_asyncio
from app import database
from app.config import settings
from app.main import app
from httpx import ASGITransport, AsyncClient

# Bearer header every test sends. Matches the dev default in Settings.auth_token.
AUTH = {"Authorization": f"Bearer {settings.auth_token}"}

# Tests must never spawn real agent workers, whatever the live .env says.
settings.dispatch_enabled = False


def _to_test_url(url: str) -> str:
    """Rewrite the configured database URL to its `<dbname>_test` sibling."""
    base, _, query = url.partition("?")
    head, _, dbname = base.rpartition("/")
    if not dbname.endswith("_test"):
        dbname += "_test"
    return f"{head}/{dbname}" + (f"?{query}" if query else "")


# The suite TRUNCATEs every table before each test, so it must never see the
# live database: rewrite the URL to a dedicated *_test sibling and hard-stop
# if that somehow didn't take.
settings.database_url = _to_test_url(settings.database_url)
assert settings.database_url.partition("?")[0].endswith("_test"), (
    f"refusing to run destructive tests against {settings.database_url!r}"
)

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


async def _provision_test_db() -> None:
    """Create the test database if missing and (re)apply the idempotent schema."""
    try:
        conn = await asyncpg.connect(settings.database_url)
    except asyncpg.InvalidCatalogNameError:
        dbname = settings.database_url.partition("?")[0].rpartition("/")[2]
        admin = await asyncpg.connect(settings.database_url.rpartition("/")[0] + "/postgres")
        await admin.execute(f'CREATE DATABASE "{dbname}"')
        await admin.close()
        conn = await asyncpg.connect(settings.database_url)
    for sql_file in sorted(_SCHEMA_DIR.glob("*.sql")):
        await conn.execute(sql_file.read_text())
    await conn.close()


asyncio.run(_provision_test_db())

_TABLES = ["discussion_messages", "discussions",
           "decisions", "leases", "artifacts", "events", "runs", "repos"]


@pytest_asyncio.fixture
async def db():
    pool = await asyncpg.create_pool(settings.database_url)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(autouse=True)
async def _clean():
    """Truncate all tables before each test, and drop the app's cached pool.

    asyncpg pools are bound to the event loop that created them; pytest-asyncio
    gives each test a fresh loop, so we clear the global pool to force the app to
    rebuild it on the current loop.
    """
    database._pool = None
    pool = await asyncpg.create_pool(settings.database_url)
    async with pool.acquire() as conn:
        await conn.execute(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
    await pool.close()
    yield
    if database._pool is not None:
        await database._pool.close()
        database._pool = None


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
