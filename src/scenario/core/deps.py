# src/scenario/core/deps.py

from scenario.core.config import settings
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.db.adapter import PostgresScenarioAdapter

# Global Infrastructure
db_handler = DatabaseHandler(settings.DATABASE_URL)
query_loader = QueryLoader(base_path="src/scenario/infra/db/queries")


async def get_scenario_engine() -> ScenarioEngine:
    """Dependency provider for the ScenarioEngine."""
    repository = PostgresScenarioAdapter(db_handler, query_loader)
    return ScenarioEngine(repository)
