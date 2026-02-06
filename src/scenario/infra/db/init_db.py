import asyncio
import logging

from scenario.core.config import settings
from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader

logger = logging.getLogger(__name__)


async def init_db(db: DatabaseHandler):
    """Initialize database tables and Apache AGE graph using external SQL files."""
    logger.info("Initializing Database...")
    loader = QueryLoader()

    async with db.get_connection() as conn:
        # 1. Load and Execute Schema SQL (Extension and Tables)
        logger.info("Running Schema Initialization...")
        init_sql = loader.load_sql("init_db")
        await conn.execute(init_sql)

        # 2. Setup AGE Path
        await conn.execute("LOAD 'age';")
        # Ensure public schema has priority during table creation
        await conn.execute('SET search_path = public, ag_catalog, "$user";')

        # 3. Apache AGE Graph
        graph_name = settings.SCENARIO_GRAPH_NAME
        logger.info(f"Checking Graph '{graph_name}'...")
        exists = await conn.fetchval(
            "SELECT count(*) FROM ag_catalog.ag_graph WHERE name = $1", graph_name
        )
        if not exists:
            await conn.execute(f"SELECT create_graph('{graph_name}');")
            logger.info(f"Graph '{graph_name}' created.")
        else:
            logger.info(f"Graph '{graph_name}' already exists.")

    logger.info("Database initialization complete.")


if __name__ == "__main__":
    handler = DatabaseHandler(settings.database_dsn)
    asyncio.run(init_db(handler))
