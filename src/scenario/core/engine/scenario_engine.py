import logging
import uuid
from typing import Any, Dict, List, Optional

from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.core.models.generation import ScenarioInjectSchema
from scenario.interfaces.rule_engine import RuleEngineRepository
from scenario.interfaces.scenario import ScenarioRepository

logger = logging.getLogger(__name__)


class ScenarioEngine:
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
        return await self.generate_pure(concept)

    async def generate_pure(self, concept: str) -> Dict:
        print(f"🧠 [LLM] Starting generation for concept: '{concept}'")
        final_state = await self.writer.run(concept)
        print("🧠 [LLM] Generation complete. Packaging data...")

        scenario_data = self._package_scenario(final_state)
        # 1. Validation BEFORE Saving: Fail fast if schema is not satisfied
        try:
            validated_data = ScenarioInjectSchema.model_validate(scenario_data)
        except Exception as e:
            # Debugging: Print problematic data if validation fails
            import json

            logger.error("=== FAILED SCENARIO DATA ===")
            logger.error(json.dumps(scenario_data, indent=2, ensure_ascii=False))
            raise e

        return await self._save_and_respond(
            validated_data.model_dump(), concept, "pure"
        )

    async def generate_grounded(self, concept: str) -> Dict:
        final_state = await self.writer.run(concept)
        scenario_data = self._package_scenario(final_state)
        if self.rule_engine:
            scenario_data = await self.rule_engine.bulk_grounding(scenario_data)

        validated_data = ScenarioInjectSchema.model_validate(scenario_data)
        return await self._save_and_respond(
            validated_data.model_dump(), concept, "delegated_grounding"
        )

    async def generate_informed(self, concept: str) -> Dict:
        final_state = await self.writer.run(concept)
        scenario_data = self._package_scenario(final_state)
        if self.rule_engine:
            assets = await self.rule_engine.get_all_assets()
            scenario_data = self._apply_local_grounding(scenario_data, assets)

        validated_data = ScenarioInjectSchema.model_validate(scenario_data)
        return await self._save_and_respond(
            validated_data.model_dump(), concept, "local_informed_grounding"
        )

    def _apply_local_grounding(self, data: Dict, assets: Dict) -> Dict:
        master_npcs = {a["name"]: a for a in assets.get("npcs", [])}
        master_enemies = {a["name"]: a for a in assets.get("enemies", [])}
        master_items = {a["name"]: a for a in assets.get("items", [])}
        master_locales = {a["name"]: a for a in assets.get("locales", [])}

        def get_rule_id(asset_dict: Dict) -> Optional[int]:
            rid = asset_dict.get("rule_id") or asset_dict.get("master_id")
            if isinstance(rid, int):
                return rid
            if isinstance(rid, str) and rid.isdigit():
                return int(rid)
            return None

        # Ground NPCs catalog
        for npc in data.get("npcs", []):
            m_npc = master_npcs.get(npc["name"])
            if m_npc:
                npc["rule_id"] = get_rule_id(m_npc)
                npc["description"] = m_npc.get(
                    "description", npc.get("description", "")
                )

        # Ground Enemies catalog
        for enemy in data.get("enemies", []):
            m_enemy = master_enemies.get(enemy["name"])
            if m_enemy:
                enemy["rule_id"] = get_rule_id(m_enemy)
                enemy["description"] = m_enemy.get(
                    "description", enemy.get("description", "")
                )

        # Ground Items catalog
        for item in data.get("items", []):
            m_item = master_items.get(item["name"])
            if m_item:
                item["rule_id"] = get_rule_id(m_item)
                item["item_type"] = m_item.get("type", item.get("item_type", "misc"))
                if "meta" not in item:
                    item["meta"] = {}
                item["meta"].update(
                    {
                        "weight": m_item.get("weight"),
                        "price": m_item.get("base_price"),
                    }
                )

        # Ground Locations in sequences
        for seq in data.get("sequences", []):
            m_loc = master_locales.get(seq["location_name"])
            if m_loc:
                seq["location_name"] = m_loc.get("name", seq.get("location_name"))

        return data

    async def _save_and_respond(self, data: Dict, concept: str, strategy: str) -> Dict:
        scenario_id = await self.repository.save_scenario(concept, data)
        return {
            "status": "success",
            "scenario_id": str(scenario_id),
            "strategy": strategy,
            "data": data,
        }

    def _package_scenario(self, state: Dict) -> Dict:
        plan = state.get("plan", {})
        content = state.get("content", {})

        # 1. Canonical ID Mapping (Order-based)
        def clean_id(val: Any) -> str:
            if not val:
                return ""
            if isinstance(val, dict):
                val = (
                    val.get("id")
                    or val.get("scenario_npc_id")
                    or val.get("scenario_enemy_id")
                    or val.get("item_id")
                )
            s = (
                str(val)
                .strip()
                .lower()
                .replace("_", "")
                .replace("-", "")
                .replace(" ", "")
            )
            # Remove common prefixes to unify "item-101" and "101"
            for prefix in ["item", "npc", "enemy", "act", "seq"]:
                if s.startswith(prefix):
                    s = s[len(prefix) :]
            return s

        seq_map = {
            clean_id(s.get("id")): f"seq-{i + 1}"
            for i, s in enumerate(content.get("sequences", []) or [])
        }
        npc_map = {
            clean_id(n.get("scenario_npc_id")): f"npc-{i + 1}"
            for i, n in enumerate(state.get("npcs", []) or [])
        }
        enemy_map = {
            clean_id(e.get("scenario_enemy_id")): f"enemy-{i + 1}"
            for i, e in enumerate(state.get("enemies", []) or [])
        }

        # Item mapping: Internal int ID -> Canonical "item-101" string
        item_map = {}
        for i, item in enumerate(state.get("items", []) or []):
            original_id = str(item.get("item_id"))
            item_map[clean_id(original_id)] = f"item-{i + 101}"

        def get_item_rule_id(item_data: Dict) -> Optional[int]:
            val = item_data.get("rule_id") or item_data.get("master_id")
            if isinstance(val, int):
                return val
            if isinstance(val, str) and val.isdigit():
                return int(val)
            return None

        # 2. Process Catalogs with New IDs
        packaged_items = []
        for i, item in enumerate(state.get("items", []) or []):
            new_id = f"item-{i + 101}"
            packaged_items.append(
                {
                    "scenario_item_id": new_id,
                    "rule_id": get_item_rule_id(item),
                    "name": item.get("name", "Untitled Item"),
                    "description": item.get("description", ""),
                    "item_type": item.get("item_type", "misc"),
                    "meta": item.get("meta", {}),
                }
            )

        packaged_npcs = []
        for i, npc in enumerate(state.get("npcs", []) or []):
            new_id = f"npc-{i + 1}"
            packaged_npcs.append(
                {
                    "scenario_npc_id": new_id,
                    "rule_id": get_item_rule_id(npc),
                    "name": npc.get("name", "Untitled NPC"),
                    "description": npc.get("description", ""),
                    "tags": npc.get("tags", []),
                    "state": npc.get("state", {}),
                    "is_departed": False,
                }
            )

        packaged_enemies = []
        for i, enemy in enumerate(state.get("enemies", []) or []):
            new_id = f"enemy-{i + 1}"
            final_drops = []
            raw_drops = enemy.get("dropped_items", []) or []
            for d in raw_drops:
                d_clean = clean_id(d)
                found_rule_id = 0
                for it in state.get("items", []) or []:
                    if clean_id(it.get("item_id")) == d_clean:
                        found_rule_id = get_item_rule_id(it)
                        break
                if found_rule_id:
                    final_drops.append(found_rule_id)

            packaged_enemies.append(
                {
                    "scenario_enemy_id": new_id,
                    "rule_id": get_item_rule_id(enemy),
                    "name": enemy.get("name", "Untitled Enemy"),
                    "description": enemy.get("description", ""),
                    "tags": enemy.get("tags", []),
                    "state": enemy.get("state", {}),
                    "dropped_items": final_drops,
                }
            )

        # 3. Package Sequences (Using New IDs)
        packaged_sequences = []
        for i, seq in enumerate(content.get("sequences", []) or []):
            new_id = f"seq-{i + 1}"
            packaged_sequences.append(
                {
                    "id": new_id,
                    "name": seq.get("name", "Untitled Sequence"),
                    "location_name": seq.get("location_name") or "Unknown Location",
                    "description": seq.get("description", ""),
                    "goal": seq.get("goal", ""),
                    "exit_triggers": seq.get("exit_triggers") or [],
                    "npcs": [
                        npc_map.get(clean_id(n))
                        for n in seq.get("npcs", []) or []
                        if clean_id(n) in npc_map
                    ],
                    "enemies": [
                        enemy_map.get(clean_id(e))
                        for e in seq.get("enemies", []) or []
                        if clean_id(e) in enemy_map
                    ],
                    "items": [
                        item_map.get(clean_id(it))
                        for it in seq.get("items", []) or []
                        if clean_id(it) in item_map
                    ],
                }
            )

        # 4. Package Acts (Using New IDs)
        packaged_acts = []
        for i, act in enumerate(plan.get("acts", []) or []):
            new_id = f"act-{i + 1}"
            region = act.get("region_name", "")
            desc = act.get("description") or act.get("region_description", "")
            final_desc = f"[{region}] {desc}" if region else desc

            packaged_acts.append(
                {
                    "id": new_id,
                    "name": act.get("name", "Untitled Act"),
                    "description": final_desc,
                    "exit_criteria": act.get("exit_criteria", ""),
                    "sequences": [
                        seq_map.get(clean_id(s))
                        for s in act.get("sequences", []) or []
                        if clean_id(s) in seq_map
                    ],
                }
            )

        # 5. Package Relations (Using New IDs)
        packaged_relations = []
        for rel in plan.get("relations", []) or []:
            f_cid, t_cid = clean_id(rel.get("from_id")), clean_id(rel.get("to_id"))
            # Source or Target can be NPC, Enemy, or Item
            f_new = npc_map.get(f_cid) or enemy_map.get(f_cid) or item_map.get(f_cid)
            t_new = npc_map.get(t_cid) or enemy_map.get(t_cid) or item_map.get(t_cid)

            if f_new and t_new:
                packaged_relations.append(
                    {
                        "from_id": f_new,
                        "to_id": t_new,
                        "relation_type": rel.get("relation_type", "neutral"),
                        "affinity": rel.get("affinity", 50),
                        "meta": rel.get("meta", {}),
                    }
                )

        return {
            "title": plan.get("title", "Untitled Scenario"),
            "description": plan.get("description") or plan.get("total_summary", ""),
            "acts": packaged_acts,
            "sequences": packaged_sequences,
            "npcs": packaged_npcs,
            "enemies": packaged_enemies,
            "items": packaged_items,
            "relations": packaged_relations,
        }

    async def inject_to_state_manager(self, scenario_id: uuid.UUID) -> Dict[str, Any]:
        import httpx

        from scenario.core.config import settings

        nested_scenario = await self.repository.get_scenario_full_graph(scenario_id)
        if not nested_scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Use ScenarioInjectSchema validation here too
        payload = ScenarioInjectSchema.model_validate(nested_scenario).model_dump()
        payload["scenario_id"] = str(scenario_id)

        async with httpx.AsyncClient() as client:
            url = f"{settings.STATE_MANAGER_URL}/state/scenario/inject"
            response = await client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            # Extract the ID generated by State Manager
            sm_scenario_id = result.get("scenario_id") or result.get("data", {}).get(
                "scenario_id"
            )

            if sm_scenario_id:
                await self.repository.update_external_id(
                    scenario_id=scenario_id, external_id=str(sm_scenario_id)
                )

            return result

    async def list_scenarios(self) -> List[Dict[str, Any]]:
        return await self.repository.list_scenarios()

    async def get_session_state(self, session_id: uuid.UUID) -> Dict[str, Any]:
        return await self.repository.get_session_state(session_id)

    async def validate_progression(
        self,
        scenario_id: str,
        act_id: str,
        seq_id: str,
        user_input: str,
        validator_agent: Any,
    ) -> Dict[str, Any]:
        def normalize(val: str) -> str:
            # Simple cleaning: lower and strip.
            # IDs like 'act-1' should be consistent now.
            return str(val).strip().lower()

        norm_act_id = normalize(act_id)
        norm_seq_id = normalize(seq_id)

        context = await self.repository.get_act_context(scenario_id, norm_act_id)
        if not context:
            # Fallback: maybe the internal DB has 'act1' instead of 'act-1'
            # due to older data but with new canonical mapping,
            # 'act-1' should be standard.
            raise ValueError(
                f"Context for scenario {scenario_id} and act {norm_act_id} not found"
            )

        sequences = context.get("sequences", [])
        current_seq = next(
            (s for s in sequences if normalize(s["id"]) == norm_seq_id), None
        )
        if not current_seq:
            raise ValueError(f"Sequence {norm_seq_id} not found in act {norm_act_id}")

        input_data = {
            "act_name": context["act"]["name"],
            "act_goal": context["act"]["goal"],
            "act_exit_criteria": context["act"]["exit_criteria"],
            "current_sequence_name": current_seq.get("name", "Unknown"),
            "current_sequence_description": current_seq.get("description", ""),
            "current_sequence_goal": current_seq.get("goal", ""),
            "exit_triggers": current_seq.get("exit_triggers") or [],
            "user_input": user_input,
        }

        # ValidatorAgent handles the logic via LLM
        return await validator_agent.run(input_data)
