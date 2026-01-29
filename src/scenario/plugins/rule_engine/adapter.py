# src/scenario/plugins/rule_engine/adapter.py

from typing import Any, Dict, List

import httpx

from scenario.core.config import settings
from scenario.interfaces.rule_engine import RuleEngineRepository


class HttpRuleEngineAdapter(RuleEngineRepository):
    """Client for communicating with the Rule Engine service."""

    def __init__(self, base_url: str = settings.RULE_ENGINE_URL):
        self.base_url = base_url

    async def search_master_data(
        self, category: str, query: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/v1/master/search"
        params = {"category": category.lower(), "query": query, "limit": limit}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                return (
                    response.json().get("results", [])
                    if response.status_code == 200
                    else []
                )
        except Exception as e:
            print(f"[!] Rule Engine Search Error: {e}")
            return []

    async def bulk_grounding(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strategy 1: Delegate grounding.
        Note: api_spec.json doesn't have a direct /master/ground endpoint.
        We'll keep this as a placeholder or it could be implemented
        by calling search for each.
        """
        return scenario_data

    async def get_all_assets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Strategy 2: Fetch all assets using Rule Engine's /info/ endpoints.
        """
        assets = {"npcs": [], "enemies": [], "items": [], "locations": []}

        async with httpx.AsyncClient() as client:
            # 1. Fetch Locales
            try:
                resp = await client.get(
                    f"{self.base_url}/info/world?include_keys=locales", timeout=10.0
                )
                if resp.status_code == 200:
                    assets["locations"] = resp.json().get("data", {}).get("locales", [])
            except Exception as e:
                print(f"[!] Rule Engine Fetch Locales Error: {e}")

            # 2. Fetch NPCs
            try:
                resp = await client.post(
                    f"{self.base_url}/info/npcs", json={"limit": 100}, timeout=10.0
                )
                if resp.status_code == 200:
                    assets["npcs"] = resp.json().get("data", {}).get("npcs", [])
            except Exception as e:
                print(f"[!] Rule Engine Fetch NPCs Error: {e}")

            # 3. Fetch Enemies
            try:
                resp = await client.post(
                    f"{self.base_url}/info/enemies", json={"limit": 100}, timeout=10.0
                )
                if resp.status_code == 200:
                    assets["enemies"] = resp.json().get("data", {}).get("enemies", [])
            except Exception as e:
                print(f"[!] Rule Engine Fetch Enemies Error: {e}")

            # 4. Fetch Items
            try:
                resp = await client.post(
                    f"{self.base_url}/info/items", json={"limit": 100}, timeout=10.0
                )
                if resp.status_code == 200:
                    assets["items"] = resp.json().get("data", {}).get("items", [])
            except Exception as e:
                print(f"[!] Rule Engine Fetch Items Error: {e}")

        return assets
