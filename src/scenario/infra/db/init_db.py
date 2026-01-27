import asyncio

from scenario.core.config import settings
from scenario.infra.db.database import DatabaseHandler


async def init_db(db: DatabaseHandler):
    """Initialize database tables and Apache AGE graph."""
    print("Initializing Relational Tables...")

    async with db.get_connection() as conn:
        graph_name = settings.SCENARIO_GRAPH_NAME
        exists = await conn.fetchval(
            "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = $1", graph_name
        )
        if not exists:
            await conn.execute(f"SELECT create_graph('{graph_name}');")
            print(f"Graph '{graph_name}' created.")
        else:
            print(f"Graph '{graph_name}' already exists.")


if __name__ == "__main__":
    handler = DatabaseHandler(settings.DATABASE_URL)
    asyncio.run(init_db(handler))
