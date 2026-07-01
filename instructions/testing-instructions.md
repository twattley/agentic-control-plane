# Testing Instructions

## Backend (pytest)

Tests live in `apps/api/tests/`, mirroring the feature structure:

```
tests/
  conftest.py               shared fixtures (db pool, httpx client)
  features/
    <name>/
      test_<behavior>.py
```

### Fixtures (conftest.py)

```python
import pytest, pytest_asyncio
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
```

### Rules

- Use a **real PostgreSQL test database** — no mocks for the DB layer.
  Set `DATABASE_URL` to a `_test` database in your local `.env`.
- Test behavior through HTTP routes (integration style), not repository functions directly.
- One assertion per test (or tightly related assertions for one behavior).

### Running

```bash
make test                               # all tests
uv run --project apps/api pytest -k payments  # filter by name
uv run --project apps/api pytest -x           # stop on first failure
```
