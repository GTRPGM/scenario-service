# src/scenario/interfaces/rule_engine.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class RuleEngineRepository(ABC):
    @abstractmethod
    async def bulk_grounding(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate grounding to Rule Engine."""
        pass

    @abstractmethod
    async def get_all_assets(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all assets for context-informed generation."""
        pass
