# src/scenario/core/engine/scenario_engine.py

import uuid
from typing import Any, Dict, List, Optional

from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.interfaces.rule_engine import RuleEngineRepository
from scenario.interfaces.scenario import ScenarioRepository


class ScenarioEngine:
    """Core engine for scenario management and generation."""

    def __init__(
        self,
        repository: ScenarioRepository,
        writer: ScenarioWriterGraph,
        rule_engine: Optional[RuleEngineRepository] = None,
    ):
        self.repository = repository
        self.writer = writer
        self.rule_engine = rule_engine

    async def generate_scenario(self, concept: str) -> Dict:
        """
        Facade for default scenario generation (Strategy: Pure).
        Maintains backward compatibility for tests/clients expecting this method.
        """
        return await self.generate_pure(concept)

    async def generate_pure(self, concept: str) -> Dict:
        """Strategy: Pure generation based only on concept."""
        final_state = await self.writer.run(concept)
        scenario_data = self._package_scenario(final_state)
        return await self._save_and_respond(scenario_data, concept, "pure")

    async def generate_grounded(self, concept: str) -> Dict:
        """Strategy: Generate first, then delegate grounding to Rule Engine."""
        final_state = await self.writer.run(concept)
        scenario_data = self._package_scenario(final_state)

        if self.rule_engine:
            scenario_data = await self.rule_engine.bulk_grounding(scenario_data)

        return await self._save_and_respond(
            scenario_data, concept, "delegated_grounding"
        )

    async def generate_informed(self, concept: str) -> Dict:
        """
        Strategy: Generate first, fetch all assets, then match & replace locally.
        """
        final_state = await self.writer.run(concept)
        scenario_data = self._package_scenario(final_state)

        if self.rule_engine:
            assets = await self.rule_engine.get_all_assets()
            scenario_data = self._apply_local_grounding(scenario_data, assets)

        return await self._save_and_respond(
            scenario_data, concept, "local_informed_grounding"
        )

    def _apply_local_grounding(self, data: Dict, assets: Dict) -> Dict:
        """
        Name-based local grounding with attribute synchronization
        from Rule Engine spec.
        """
        master_npcs = {a["name"]: a for a in assets.get("npcs", [])}
        master_enemies = {a["name"]: a for a in assets.get("enemies", [])}
        master_items = {a["name"]: a for a in assets.get("items", [])}
        master_locs = {
            a["name"]: a for a in assets.get("locales", [])
        }  # Rule engine uses 'locales'

        for seq in data.get("sequences", []):
            # 1. Match Location
            m_loc = master_locs.get(seq["location_name"])
            if m_loc:
                seq["location_master_id"] = str(m_loc.get("locale_id"))
                seq["location_name"] = m_loc.get("name", seq["location_name"])
                seq["location_theme"] = m_loc.get("theme", seq["location_theme"])
                seq["location_description"] = m_loc.get(
                    "description", seq["location_description"]
                )
                seq["danger_min"] = m_loc.get("danger_min", seq.get("danger_min", 1))
                seq["danger_max"] = m_loc.get("danger_max", seq.get("danger_max", 10))

            # 2. Match NPCs
            for npc in seq.get("npcs", []):
                m_npc = master_npcs.get(npc["name"])
                if m_npc:
                    npc["master_id"] = str(m_npc.get("npc_id"))
                    npc["name"] = m_npc.get("name", npc["name"])
                    occ = m_npc.get("occupation", "")
                    desc = m_npc.get("description", "")
                    npc["description"] = f"[{occ}] {desc}"
                    npc["state"]["numeric"]["difficulty"] = m_npc.get(
                        "base_difficulty", 10
                    )
                    # Sync other available fields if needed

            # 3. Match Enemies
            for enemy in seq.get("enemies", []):
                m_enemy = master_enemies.get(enemy["name"])
                if m_enemy:
                    enemy["master_id"] = str(m_enemy.get("enemy_id"))
                    enemy["name"] = m_enemy.get("name", enemy["name"])
                    enemy["description"] = m_enemy.get(
                        "description", enemy["description"]
                    )
                    enemy["tags"] = [m_enemy.get("type", "enemy")]
                    enemy["state"]["numeric"]["HP"] = (
                        m_enemy.get("base_difficulty", 1) * 10
                    )  # Heuristic

            # 4. Match Items
            for item in seq.get("items", []):
                m_item = master_items.get(item["name"])
                if m_item:
                    item["master_id"] = str(m_item.get("item_id"))
                    item["name"] = m_item.get("name", item["name"])
                    item["description"] = m_item.get("description", item["description"])
                    item["item_type"] = m_item.get("type", item["item_type"])
                    item["meta"] = {
                        "weight": m_item.get("weight"),
                        "grade": m_item.get("grade"),
                        "price": m_item.get("base_price"),
                        "effect_value": m_item.get("effect_value"),
                    }

        return data

    async def _save_and_respond(self, data: Dict, concept: str, strategy: str) -> Dict:
        scenario_id = uuid.uuid4()
        await self.repository.save_scenario(scenario_id, concept, data)
        return {
            "status": "success",
            "scenario_id": str(scenario_id),
            "strategy": strategy,
            "data": data,
        }

    def _package_scenario(self, state: Dict) -> Dict:
        plan = state["plan"]
        content = state["content"]

        all_npcs = []
        all_enemies = []
        all_items = []

        for seq in content.get("sequences", []):
            all_npcs.extend(seq.get("npcs", []))
            all_enemies.extend(seq.get("enemies", []))
            all_items.extend(seq.get("items", []))

        return {
            "title": plan.get("title", "Untitled Scenario"),
            "description": plan.get("description", ""),
            "summary": plan.get("total_summary"),
            "difficulty": plan.get("difficulty", "normal"),
            "genre": plan.get("genre", "fantasy"),
            "tags": plan.get("tags", []),
            "total_acts": plan.get("total_acts", 1),
            "acts": plan.get("acts"),
            "sequences": content.get("sequences"),
            "npcs": all_npcs,
            "enemies": all_enemies,
            "items": all_items,
            "relations": plan.get("relations", []),
        }

    async def list_scenarios(self) -> List[Dict]:
        return await self.repository.list_scenarios()

    async def validate_progression(
        self,
        scenario_id: str,
        act_id: str,
        seq_id: str,
        user_input: str,
        validator_agent: Any,
    ) -> Dict[str, Any]:
        """
        Orchestrates the validation process by fetching act context
        and calling the validator agent.
        """
        # Fetch Act and associated Sequences for context
        context = await self.repository.get_act_context(uuid.UUID(scenario_id), act_id)
        if not context:
            raise ValueError(f"Act {act_id} not found in scenario {scenario_id}")

        act_data = context["act"]
        all_seqs = context["sequences"]

        # Find current sequence
        current_seq = next((s for s in all_seqs if s["id"] == seq_id), None)
        if not current_seq:
            raise ValueError(f"Sequence {seq_id} not found in act {act_id}")

        # Construct Agent Request
        agent_request = {
            "scenario_id": scenario_id,
            "current_act": act_data,
            "current_sequence": current_seq,
            "available_sequences": all_seqs,  # All POIs in the region
            "user_input": user_input,
            "context": {},  # Can be extended with global relations if needed
        }

        return await validator_agent.run(agent_request)

    async def get_session_state(self, session_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch session state via repository."""
        # Assuming repository has get_session_state. Adapter has it.
        # But ScenarioRepository interface might not have it.
        # We should probably cast or ensure interface has it.
        # Since Python is dynamic, if the instance has it, it works.
        # But good practice is to add to interface. I will assume dynamic dispatch for now or that Adapter IS the repository.
        if hasattr(self.repository, "get_session_state"):
            return await self.repository.get_session_state(session_id)
        return {}
