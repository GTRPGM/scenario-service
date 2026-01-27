from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg


class DatabaseHandler:
    """Infrastructure: Low-level asyncpg connection pool handler."""

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize the connection pool and set up AGE."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn,
                init=self._initialize_age,
                min_size=2,
                max_size=10,
            )

    async def _initialize_age(self, conn: asyncpg.Connection) -> None:
        """Load Apache AGE extension and set up search path for the connection."""
        await conn.execute("LOAD 'age';")
        await conn.execute("SET search_path = ag_catalog, '$user', public;")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Provides a connection from the pool as a context manager."""
        if self.pool is None:
            await self.connect()
        async with self.pool.acquire() as conn:
            yield conn

    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        """Execute a query and fetch all results."""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args) -> str:
        """Execute a query without returning results."""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)

    async def close(self) -> None:
        """Gracefully close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
