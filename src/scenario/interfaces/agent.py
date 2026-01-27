# src/scenario/interfaces/agent.py

from abc import ABC, abstractmethod
from typing import Any, Dict


class ScenarioAgent(ABC):
    """Abstract interface for scenario generation agents."""

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent logic with given input."""
        pass
