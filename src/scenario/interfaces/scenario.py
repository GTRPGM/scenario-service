from abc import ABC, abstractmethod
from typing import Any, Dict, List
from uuid import UUID


class ScenarioRepository(ABC):
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
        pass

    @abstractmethod
    async def get_scenario_full_graph(self, scenario_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, data: Dict
    ) -> None:
        pass

    @abstractmethod
    async def get_session_state(self, session_id: UUID) -> Dict[str, Any]:
        pass
