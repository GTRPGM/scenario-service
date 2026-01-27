# src/scenario/plugins/db/adapter.py

from typing import Dict
from uuid import UUID

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader
from scenario.interfaces.scenario import ScenarioRepository


class PostgresScenarioAdapter(ScenarioRepository):
    """PostgreSQL + AGE implementation of ScenarioRepository."""

    def __init__(self, db: DatabaseHandler, loader: QueryLoader):
        self.db = db
        self.loader = loader

    async def get_session_state(self, session_id: UUID) -> Dict:
        # Placeholder for DB query
        return {
            "current_act_id": "act_01",
            "current_sequence_id": "seq_01",
            "conditions": ["플레이어가 촌장과 대화함"],
        }

    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, context: Dict
    ) -> None:
        sql = self.loader.load_sql("update_session_state")
        await self.db.execute(sql, act_id, seq_id, "{}", session_id)

    async def get_scenario_graph(self, scenario_id: UUID):
        raise NotImplementedError
