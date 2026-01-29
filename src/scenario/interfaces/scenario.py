# src/scenario/interfaces/scenario.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID


class ScenarioRepository(ABC):
    """Abstract interface for scenario data access (Templates only)."""

    @abstractmethod
    async def save_scenario(
        self, scenario_id: UUID, concept: str, data: Dict[str, Any]
    ) -> None:
        pass

    @abstractmethod
    async def list_scenarios(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_act_context(self, scenario_id: UUID, act_id: str) -> Dict[str, Any]:
        """Fetch act details and all its sequences for validation context."""
        pass
