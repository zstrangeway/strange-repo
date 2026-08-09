import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

DEFAULT_URL = "postgresql+asyncpg://postgres@127.0.0.1:5432/postgres"


def database_url() -> str:
    """Normalise DATABASE_URL to the async driver.

    Fly and most Postgres providers hand out postgres:// or postgresql://,
    neither of which selects an async driver.
    """
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine: AsyncEngine = create_async_engine(database_url(), pool_pre_ping=True)


async def is_reachable() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
