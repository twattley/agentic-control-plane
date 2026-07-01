import pytest_asyncio
import asyncpg
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.config import settings


@pytest_asyncio.fixture
async def db():
    pool = await asyncpg.create_pool(settings.database_url)
    yield pool
    await pool.close()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
