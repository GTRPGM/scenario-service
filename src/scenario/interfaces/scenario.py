from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
from uuid import UUID


class ScenarioRepository(ABC):
    @abstractmethod
    async def save_scenario(self, concept: str, data: Dict[str, Any]) -> UUID:
        """
        Persist the generated scenario data to the database
        and return the generated ID.
        """
        ...

    @abstractmethod
    async def list_scenarios(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_act_context(
        self, scenario_id: Union[UUID, str], act_id: str
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_external_id(
        self, scenario_id: UUID, external_id: str, provider: str = "state_manager"
    ) -> None:
        """Link an internal scenario to an external service ID."""
        pass

    @abstractmethod
    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, data: Dict
    ) -> None:
        pass

    @abstractmethod
    async def get_session_state(self, session_id: UUID) -> Dict[str, Any]:
        pass
