# src/scenario/infra/db/database.py

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg


class DatabaseHandler:
    """
    Infrastructure:
    Low-level asyncpg connection pool handler with lazy connection support.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self._connecting_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Initialize the connection pool. Safe to call multiple times."""
        if self.pool:
            return

        async with self._connecting_lock:
            if self.pool:
                return

            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.dsn,
                    init=self._initialize_age,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                )
            except Exception as e:
                # Log but don't raise here; let the caller decide
                raise ConnectionError(
                    f"Could not connect to PostgreSQL at {self.dsn}: {e}"
                ) from e

    async def _initialize_age(self, conn: asyncpg.Connection) -> None:
        """Set up Apache AGE for each new connection."""
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, '$user', public;")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Provides a connection from the pool, connecting lazily if necessary."""
        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args) -> str:
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)

    async def close(self) -> None:
        """Gracefully close the pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
