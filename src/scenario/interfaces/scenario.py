# src/scenario/interfaces/scenario.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID


class ScenarioRepository(ABC):
    """Abstract interface for scenario data access."""

    @abstractmethod
    async def save_scenario(
        self, scenario_id: UUID, concept: str, data: Dict[str, Any]
    ) -> None:
        pass

    @abstractmethod
    async def list_scenarios(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_scenario_full_graph(self, scenario_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def create_session(
        self, session_id: UUID, scenario_id: UUID, initial_act: str, initial_seq: str
    ) -> None:
        pass

    @abstractmethod
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active/stored session states."""
        pass

    @abstractmethod
    async def get_session_state(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, context: Dict[str, Any]
    ) -> None:
        pass
