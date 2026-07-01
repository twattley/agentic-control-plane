import asyncpg
import pytest_asyncio
from app import database
from app.config import settings
from app.main import app
from httpx import ASGITransport, AsyncClient

# Bearer header every test sends. Matches the dev default in Settings.auth_token.
AUTH = {"Authorization": f"Bearer {settings.auth_token}"}

_TABLES = ["decisions", "leases", "artifacts", "events", "runs", "repos"]


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
