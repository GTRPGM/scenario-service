# src/scenario/interfaces/scenario.py

from abc import ABC, abstractmethod
from typing import Dict
from uuid import UUID

from scenario.core.models.scenario import ScenarioGraph


class ScenarioRepository(ABC):
    """Abstract interface for scenario data access."""

    @abstractmethod
    async def get_session_state(self, session_id: UUID) -> Dict:
        pass

    @abstractmethod
    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, context: Dict
    ) -> None:
        pass

    @abstractmethod
    async def get_scenario_graph(self, scenario_id: UUID) -> ScenarioGraph:
        pass
