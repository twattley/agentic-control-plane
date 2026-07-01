import asyncio
import glob
import os

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.database_url)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def _run_migrations() -> None:
    schema_dir = os.path.join(os.path.dirname(__file__), "..", "schema")
    migration_files = sorted(glob.glob(os.path.join(schema_dir, "*.sql")))
    pool = await asyncpg.create_pool(dsn=settings.database_url)
    try:
        async with pool.acquire() as conn:
            for path in migration_files:
                with open(path) as f:
                    sql = f.read()
                await conn.execute(sql)
                print(f"  applied {os.path.basename(path)}")
    finally:
        await pool.close()


def apply_migrations() -> None:
    asyncio.run(_run_migrations())
