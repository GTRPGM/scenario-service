import logging
import re
import uuid
from inspect import isawaitable
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

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

        if not bool(final_state.get("is_consistent", False)):
            reviews = final_state.get("reviews", []) or []
            try:
                plan = final_state.get("plan") or {}
                content = final_state.get("content") or {}
                npc_m = plan.get("npc_manifest") or []
                enemy_m = plan.get("enemy_manifest") or []
                item_m = plan.get("item_manifest") or []
                seqs = (
                    (content.get("sequences") or [])
                    if isinstance(content, dict)
                    else []
                )
                seq_counts = []
                for s in seqs:
                    if not isinstance(s, dict):
                        continue
                    sid = s.get("id")
                    npcs = s.get("npcs") or []
                    enemies = s.get("enemies") or []
                    items = s.get("items") or []
                    seq_counts.append(
                        {
                            "id": sid,
                            "sequence_type": s.get("sequence_type"),
                            "npcs": len(npcs) if isinstance(npcs, list) else None,
                            "enemies": len(enemies)
                            if isinstance(enemies, list)
                            else None,
                            "items": len(items) if isinstance(items, list) else None,
                        }
                    )
                logger.error(
                    "Scenario generation rejected by reviewer. acts=%s seqs=%s npc_m=%s enemy_m=%s item_m=%s seq_counts=%s reviews=%s",
                    len(plan.get("acts") or []) if isinstance(plan, dict) else None,
                    len(seqs),
                    len(npc_m) if isinstance(npc_m, list) else None,
                    len(enemy_m) if isinstance(enemy_m, list) else None,
                    len(item_m) if isinstance(item_m, list) else None,
                    seq_counts,
                    reviews,
                )
            except Exception:
                logger.error(
                    "Scenario generation rejected by reviewer. reviews=%s", reviews
                )
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Scenario generation inconsistent",
                    "reviews": reviews,
                },
            )

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

        def get_master_id(asset_dict: Dict) -> Optional[str]:
            mid = asset_dict.get("master_id") or asset_dict.get("rule_id")
            return str(mid) if mid is not None else None

        def get_rule_id(asset_dict: Dict) -> Optional[int]:
            raw = asset_dict.get("rule_id") or asset_dict.get("master_id")
            if raw is None:
                return None
            if isinstance(raw, int):
                return raw
            text = str(raw).strip()
            if text.isdigit():
                return int(text)
            digits = "".join(ch for ch in text if ch.isdigit())
            return int(digits) if digits else None

        # Ground NPCs catalog
        for npc in data.get("npcs", []):
            m_npc = master_npcs.get(npc["name"])
            if m_npc:
                npc["master_id"] = get_master_id(m_npc)
                rid = get_rule_id(m_npc)
                if rid is not None:
                    npc["rule_id"] = rid
                npc["description"] = m_npc.get(
                    "description", npc.get("description", "")
                )

        # Ground Enemies catalog
        for enemy in data.get("enemies", []):
            m_enemy = master_enemies.get(enemy["name"])
            if m_enemy:
                enemy["master_id"] = get_master_id(m_enemy)
                rid = get_rule_id(m_enemy)
                if rid is not None:
                    enemy["rule_id"] = rid
                enemy["description"] = m_enemy.get(
                    "description", enemy.get("description", "")
                )

        # Ground Items catalog
        for item in data.get("items", []):
            m_item = master_items.get(item["name"])
            if m_item:
                item["master_id"] = get_master_id(m_item)
                rid = get_rule_id(m_item)
                if rid is not None:
                    item["rule_id"] = rid
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
        def normalize_rule_id(val: Any) -> int:
            if isinstance(val, int):
                return val
            if val is None:
                return 0
            s = str(val).strip()
            if s == "":
                return 0
            if s.isdigit():
                return int(s)
            digits = "".join(ch for ch in s if ch.isdigit())
            return int(digits) if digits else 0

        def clean_id(val: Any) -> str:
            if not val:
                return ""
            if isinstance(val, dict):
                val = (
                    val.get("id")
                    or val.get("scenario_npc_id")
                    or val.get("scenario_enemy_id")
                    or val.get("scenario_item_id")
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
            # Normalize leading zeros so "01" and "1" map to the same key.
            if s.isdigit():
                s = s.lstrip("0") or "0"
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

        # Item mapping: Internal int ID -> Canonical string ID
        item_map = {}
        for i, item in enumerate(state.get("items", []) or []):
            original_id = str(item.get("scenario_item_id") or item.get("item_id"))
            item_map[clean_id(original_id)] = f"{i + 101}"

        # 2. Process Catalogs with New IDs
        packaged_items = []
        for i, item in enumerate(state.get("items", []) or []):
            new_id = str(i + 101)
            packaged_items.append(
                {
                    "scenario_item_id": new_id,
                    "rule_id": normalize_rule_id(
                        item.get("rule_id", item.get("master_id"))
                    ),
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
                    "rule_id": normalize_rule_id(
                        npc.get("rule_id", npc.get("master_id"))
                    ),
                    "name": npc.get("name", "Untitled NPC"),
                    "description": npc.get("description", ""),
                    "tags": npc.get("tags", []),
                    "state": npc.get("state", {}),
                }
            )

        packaged_enemies = []
        for i, enemy in enumerate(state.get("enemies", []) or []):
            new_id = f"enemy-{i + 1}"
            packaged_enemies.append(
                {
                    "scenario_enemy_id": new_id,
                    "rule_id": normalize_rule_id(
                        enemy.get("rule_id", enemy.get("master_id"))
                    ),
                    "name": enemy.get("name", "Untitled Enemy"),
                    "description": enemy.get("description", ""),
                    "tags": enemy.get("tags", []),
                    "state": enemy.get("state", {}),
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
                    "sequence_type": seq.get("sequence_type", "Exploration"),
                    "location_name": seq.get("location_name") or "Unknown Location",
                    "location_master_id": seq.get("location_master_id"),
                    "location_theme": seq.get("location_theme", ""),
                    "location_description": seq.get("location_description", ""),
                    "danger_min": seq.get("danger_min", 1),
                    "danger_max": seq.get("danger_max", 10),
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
            packaged_acts.append(
                {
                    "id": new_id,
                    "name": act.get("name", "Untitled Act"),
                    "region_name": act.get("region_name", ""),
                    "region_description": act.get("region_description", ""),
                    "description": act.get("description"),
                    "goal": act.get("goal", ""),
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
            "summary": plan.get("total_summary") or plan.get("summary", ""),
            "description": plan.get("description"),
            "difficulty": plan.get("difficulty", "normal"),
            "genre": plan.get("genre", "fantasy"),
            "tags": plan.get("tags", []),
            "total_acts": plan.get("total_acts", len(packaged_acts)),
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

        payload = self._to_state_injection_payload(nested_scenario)
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

    def _normalize_debug_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if any(
            k in payload for k in ("planner_output", "writer_output", "relation_output")
        ):
            planner = payload.get("planner_output") or {}
            writer = payload.get("writer_output") or {}
            relation = payload.get("relation_output") or {}
            payload = {
                "title": planner.get("title", "DEBUG_SCENARIO"),
                "description": planner.get("description", ""),
                "summary": planner.get(
                    "total_summary", planner.get("description", "")
                ),
                "difficulty": planner.get("difficulty", "normal"),
                "genre": planner.get("genre", "debug"),
                "tags": planner.get("tags", ["debug"]),
                "total_acts": planner.get(
                    "total_acts", len(planner.get("acts", []) or [])
                ),
                "acts": planner.get("acts", []),
                "sequences": writer.get("sequences", []),
                "npcs": planner.get("npc_manifest", []),
                "enemies": planner.get("enemy_manifest", []),
                "items": planner.get("item_manifest", []),
                "relations": relation.get("relations", planner.get("relations", [])),
            }

        normalized = dict(payload)
        normalized["npcs"] = self._normalize_debug_npcs(normalized.get("npcs", []))
        normalized["enemies"] = self._normalize_debug_enemies(
            normalized.get("enemies", [])
        )
        normalized["items"] = self._normalize_debug_items(normalized.get("items", []))
        normalized["relations"] = [
            {
                "from_id": str(r.get("from_id", "")),
                "to_id": str(r.get("to_id", "")),
                "relation_type": r.get("relation_type", "neutral"),
                "affinity": r.get("affinity", 50),
                "meta": r.get("meta", {}),
            }
            for r in normalized.get("relations", []) or []
            if r.get("from_id") and r.get("to_id")
        ]
        return normalized

    def _normalize_debug_npcs(self, npcs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for i, npc in enumerate(npcs or [], start=1):
            npc_id = str(npc.get("scenario_npc_id") or npc.get("id") or f"npc-{i}")
            out.append(
                {
                    **npc,
                    "scenario_npc_id": npc_id,
                    "name": npc.get("name", npc_id),
                    "description": npc.get("description", npc.get("concept", "")),
                    "role": npc.get("role", "supporting"),
                    "location": npc.get("location", ""),
                }
            )
        return out

    def _normalize_debug_enemies(
        self, enemies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        out = []
        for i, enemy in enumerate(enemies or [], start=1):
            enemy_id = str(
                enemy.get("scenario_enemy_id") or enemy.get("id") or f"enemy-{i}"
            )
            out.append(
                {
                    **enemy,
                    "scenario_enemy_id": enemy_id,
                    "name": enemy.get("name", enemy_id),
                    "description": enemy.get(
                        "description", enemy.get("concept", "")
                    ),
                    "stats": enemy.get(
                        "stats", {"hp": 10, "attack": 5, "defense": 3}
                    ),
                    "skills": enemy.get("skills", []),
                }
            )
        return out

    def _normalize_debug_items(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        out = []
        for i, item in enumerate(items or [], start=1):
            item_id = str(
                item.get("scenario_item_id")
                or item.get("item_id")
                or item.get("id")
                or f"item-{i}"
            )
            out.append(
                {
                    **item,
                    "scenario_item_id": item_id,
                    "name": item.get("name", item_id),
                    "description": item.get("description", item.get("concept", "")),
                    "item_type": item.get("item_type", "misc"),
                    "effects": item.get("effects", []),
                }
            )
        return out

    async def save_and_inject_debug(
        self,
        payload: Dict[str, Any],
        *,
        concept: str = "debug-direct-inject",
        inject_to_state: bool = True,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        normalized: Dict[str, Any] = self._normalize_debug_payload(payload)
        normalized.setdefault("title", "DEBUG_SCENARIO")
        normalized.setdefault("summary", normalized.get("description", ""))
        normalized.setdefault("description", normalized.get("summary", ""))
        normalized.setdefault("difficulty", "normal")
        normalized.setdefault("genre", "debug")
        normalized.setdefault("tags", ["debug"])
        normalized.setdefault("acts", [])
        normalized.setdefault("sequences", [])
        normalized.setdefault("npcs", [])
        normalized.setdefault("enemies", [])
        normalized.setdefault("items", [])
        normalized.setdefault("relations", [])
        normalized.setdefault(
            "total_acts", max(1, len(normalized.get("acts", [])) or 1)
        )

        # Allow simplified payloads without explicit acts by creating act-1.
        if not normalized.get("acts") and normalized.get("sequences"):
            seq_ids = [
                str(s.get("id"))
                for s in normalized.get("sequences", [])
                if isinstance(s, dict) and s.get("id")
            ]
            normalized["acts"] = [
                {
                    "id": "act-1",
                    "name": "Debug Act",
                    "description": "Auto-generated act for debug injection",
                    "goal": "debug",
                    "exit_criteria": "debug",
                    "sequences": seq_ids,
                }
            ]
            normalized["total_acts"] = 1

        self._validate_state_payload_references(normalized)
        replace_fn = getattr(self.repository, "save_or_replace_scenario_by_concept", None)
        if callable(replace_fn):
            maybe = replace_fn(concept, normalized)
            if isawaitable(maybe):
                scenario_id = await maybe
            else:
                scenario_id = await self.repository.save_scenario(concept, normalized)
        else:
            scenario_id = await self.repository.save_scenario(concept, normalized)

        result: Dict[str, Any] = {
            "status": "success",
            "scenario_service_id": str(scenario_id),
            "saved": True,
            "injected": False,
        }

        if inject_to_state:
            inject_result = await self.inject_to_state_manager(scenario_id)
            result["injected"] = True
            result["state_injection_result"] = inject_result
            result["state_manager_scenario_id"] = inject_result.get(
                "scenario_id"
            ) or inject_result.get("data", {}).get("scenario_id")

        return result

    def _parse_transition_id(self, raw_id: str, prefix: str) -> tuple[int, str]:
        value = str(raw_id or "").strip().lower()
        if not value:
            raise ValueError(f"{prefix}_id is required")

        normalized = value.replace("_", "-")
        if not normalized.startswith(prefix):
            normalized = f"{prefix}-{normalized}"

        nums = re.findall(r"\d+", normalized)
        if not nums:
            raise ValueError(f"Invalid {prefix}_id format: {raw_id}")

        canonical = f"{prefix}-{'-'.join(nums)}"
        return int(nums[0]), canonical

    async def transition_session(
        self, session_id: str, next_seq_id: str, next_act_id: str | None = None
    ) -> Dict[str, Any]:
        import httpx

        from scenario.core.config import settings

        async with httpx.AsyncClient() as client:
            if next_act_id:
                act_num, act_id = self._parse_transition_id(next_act_id, "act")
                _, seq_id = self._parse_transition_id(next_seq_id, "seq")
                payload = {
                    "new_act": act_num,
                    "new_act_id": act_id,
                    "new_sequence_id": seq_id,
                }
                url = f"{settings.STATE_MANAGER_URL}/state/session/{session_id}/act"
                response = await client.put(url, json=payload)
            else:
                seq_num, seq_id = self._parse_transition_id(next_seq_id, "seq")
                payload = {
                    "new_sequence": seq_num,
                    "new_sequence_id": seq_id,
                }
                url = (
                    f"{settings.STATE_MANAGER_URL}/state/session/{session_id}/sequence"
                )
                response = await client.put(url, json=payload)

            response.raise_for_status()
            body = response.json()
            return {
                "status": "success",
                "data": body.get("data", body),
            }

    def _coerce_rule_id(self, value: Any, *, field: str) -> int:
        if isinstance(value, int):
            return value
        if value is None:
            return 0
        text = str(value).strip()
        if text == "":
            return 0
        if text.isdigit():
            return int(text)
        match = re.search(r"\d+", text)
        if match:
            return int(match.group(0))
        raise ValueError(f"Invalid {field}: {value}")

    def _to_state_injection_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Build item mapping first so sequence refs/drops can be normalized.
        state_items: List[Dict[str, Any]] = []
        item_id_map: Dict[str, str] = {}
        item_rule_map: Dict[str, int] = {}

        for item in data.get("items", []) or []:
            scenario_item_id = str(
                item.get("scenario_item_id", item.get("item_id", ""))
            ).strip()
            if not scenario_item_id:
                continue
            rule_id = self._coerce_rule_id(
                item.get("rule_id", item.get("master_id")),
                field=f"item[{scenario_item_id}].rule_id",
            )
            state_item = {
                "scenario_item_id": scenario_item_id,
                "rule_id": rule_id,
                "name": item.get("name", "Untitled Item"),
                "description": item.get("description", ""),
                "item_type": item.get("item_type", "misc"),
                "meta": item.get("meta", {}),
            }
            state_items.append(state_item)
            item_id_map[scenario_item_id] = scenario_item_id
            item_id_map[scenario_item_id.lower()] = scenario_item_id
            item_rule_map[scenario_item_id] = rule_id

        state_npcs = []
        for npc in data.get("npcs", []) or []:
            scenario_npc_id = str(npc.get("scenario_npc_id", "")).strip()
            if not scenario_npc_id:
                continue
            state_npcs.append(
                {
                    "scenario_npc_id": scenario_npc_id,
                    "rule_id": self._coerce_rule_id(
                        npc.get("rule_id", npc.get("master_id")),
                        field=f"npc[{scenario_npc_id}].rule_id",
                    ),
                    "name": npc.get("name", "Untitled NPC"),
                    "description": npc.get("description", ""),
                    "tags": npc.get("tags", []),
                    "state": npc.get("state", {}),
                    "is_departed": npc.get("is_departed", False),
                }
            )

        state_enemies = []
        for enemy in data.get("enemies", []) or []:
            scenario_enemy_id = str(enemy.get("scenario_enemy_id", "")).strip()
            if not scenario_enemy_id:
                continue
            state_enemies.append(
                {
                    "scenario_enemy_id": scenario_enemy_id,
                    "rule_id": self._coerce_rule_id(
                        enemy.get("rule_id", enemy.get("master_id")),
                        field=f"enemy[{scenario_enemy_id}].rule_id",
                    ),
                    "name": enemy.get("name", "Untitled Enemy"),
                    "description": enemy.get("description", ""),
                    "tags": enemy.get("tags", []),
                    "state": enemy.get("state", {}),
                }
            )

        state_sequences = []
        for seq in data.get("sequences", []) or []:
            mapped_items = []
            for ref in seq.get("items", []) or []:
                key = str(ref).strip()
                mapped = item_id_map.get(key) or item_id_map.get(key.lower())
                if mapped:
                    mapped_items.append(mapped)
            metadata = dict(seq.get("metadata") or {})
            # Backward compatibility:
            # legacy payloads may carry sequence_type at top-level.
            if not metadata.get("sequence_type") and seq.get("sequence_type"):
                metadata["sequence_type"] = seq.get("sequence_type")
            state_sequences.append(
                {
                    "id": seq.get("id"),
                    "name": seq.get("name", "Untitled Sequence"),
                    "location_name": seq.get("location_name"),
                    "description": seq.get("description"),
                    "goal": seq.get("goal"),
                    "exit_triggers": seq.get("exit_triggers", []),
                    "metadata": metadata,
                    "npcs": seq.get("npcs", []),
                    "enemies": seq.get("enemies", []),
                    "items": mapped_items,
                }
            )

        state_acts = []
        for act in data.get("acts", []) or []:
            state_acts.append(
                {
                    "id": act.get("id"),
                    "name": act.get("name", "Untitled Act"),
                    "description": act.get("description")
                    or act.get("region_description"),
                    "exit_criteria": act.get("exit_criteria"),
                    "sequences": act.get("sequences", []),
                }
            )

        state_relations = []
        for rel in data.get("relations", []) or []:
            state_relations.append(
                {
                    "from_id": str(rel.get("from_id", "")),
                    "to_id": str(rel.get("to_id", "")),
                    "relation_type": rel.get("relation_type", "neutral"),
                    "affinity": rel.get("affinity", 50),
                    "meta": rel.get("meta", {}),
                }
            )

        payload = {
            "title": data.get("title", "Untitled Scenario"),
            "description": data.get("description"),
            "acts": state_acts,
            "sequences": state_sequences,
            "npcs": state_npcs,
            "enemies": state_enemies,
            "items": state_items,
            "relations": state_relations,
        }
        self._validate_state_payload_references(payload)
        return payload

    def _validate_state_payload_references(self, payload: Dict[str, Any]) -> None:
        """Validate cross references before handing payload to State Manager."""
        acts = payload.get("acts", []) or []
        sequences = payload.get("sequences", []) or []
        npcs = payload.get("npcs", []) or []
        enemies = payload.get("enemies", []) or []
        items = payload.get("items", []) or []
        relations = payload.get("relations", []) or []

        seq_ids = {str(s.get("id")) for s in sequences}
        npc_ids = {str(n.get("scenario_npc_id")) for n in npcs}
        enemy_ids = {str(e.get("scenario_enemy_id")) for e in enemies}
        item_ids = {str(i.get("scenario_item_id")) for i in items}
        entity_ids = npc_ids | enemy_ids | item_ids

        for act in acts:
            act_id = str(act.get("id"))
            for seq_id in act.get("sequences", []) or []:
                if str(seq_id) not in seq_ids:
                    raise ValueError(
                        f"Invalid act[{act_id}].sequences reference: {seq_id}"
                    )

        for seq in sequences:
            sid = str(seq.get("id"))
            for nid in seq.get("npcs", []) or []:
                if str(nid) not in npc_ids:
                    raise ValueError(f"Invalid sequence[{sid}].npcs reference: {nid}")
            for eid in seq.get("enemies", []) or []:
                if str(eid) not in enemy_ids:
                    raise ValueError(
                        f"Invalid sequence[{sid}].enemies reference: {eid}"
                    )
            for iid in seq.get("items", []) or []:
                if str(iid) not in item_ids:
                    raise ValueError(f"Invalid sequence[{sid}].items reference: {iid}")

        for rel in relations:
            from_id = str(rel.get("from_id", ""))
            to_id = str(rel.get("to_id", ""))
            if from_id not in entity_ids or to_id not in entity_ids:
                raise ValueError(
                    f"Invalid relation reference: from={from_id}, to={to_id}"
                )

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
            "act_id": norm_act_id,
            "act_name": context["act"]["name"],
            "act_goal": context["act"]["goal"],
            "act_exit_criteria": context["act"]["exit_criteria"],
            "current_sequence_id": current_seq.get("id"),
            "current_sequence_name": current_seq.get("name", "Unknown"),
            "current_sequence_description": current_seq.get("description", ""),
            "current_sequence_goal": current_seq.get("goal", ""),
            "exit_triggers": current_seq.get("exit_triggers") or [],
            "available_sequences": [s.get("id") for s in sequences if s.get("id")],
            "user_input": user_input,
        }

        # ValidatorAgent handles the logic via LLM
        result = await validator_agent.run(input_data)
        result = self._apply_transition_fallback(
            result=result,
            user_input=user_input,
            current_seq=current_seq,
            sequences=sequences,
        )
        result = await self._ensure_transition_pair(
            result=result,
            scenario_id=scenario_id,
            current_act_id=norm_act_id,
            current_seq_id=norm_seq_id,
            current_act_sequences=sequences,
        )
        result = self._guard_non_forward_sequence_transition(
            result=result,
            current_seq_id=norm_seq_id,
            sequences=sequences,
        )
        result = await self._recover_act_boundary_transition(
            result=result,
            scenario_id=scenario_id,
            current_act_id=norm_act_id,
            current_seq_id=norm_seq_id,
            current_act_sequences=sequences,
            user_input=user_input,
            current_seq=current_seq,
        )
        return self._mark_should_end_if_terminal_triggered(
            result=result,
            current_seq_id=norm_seq_id,
            sequences=sequences,
        )

    async def _ensure_transition_pair(
        self,
        result: Dict[str, Any],
        scenario_id: str,
        current_act_id: str,
        current_seq_id: str,
        current_act_sequences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result

        def normalize(val: Any) -> str:
            return str(val or "").strip().lower()

        next_act_id = result.get("next_act_id")
        next_seq_id = result.get("next_seq_id")

        # LLM may only signal trigger at an act boundary
        # without explicit transition IDs.
        # In that case, advance to the next act's first sequence when resolvable.
        if (
            not next_act_id
            and not next_seq_id
            and bool(result.get("is_triggered"))
            and self._is_terminal_sequence(current_seq_id, current_act_sequences)
        ):
            inferred_next_act_id = self._infer_next_act_id(current_act_id)
            if inferred_next_act_id:
                next_ctx = await self.repository.get_act_context(
                    scenario_id, inferred_next_act_id
                )
                next_sequences = (next_ctx or {}).get("sequences", [])
                if next_sequences:
                    first_seq = next_sequences[0].get("id")
                    if first_seq:
                        reason = str(result.get("reason") or "").strip()
                        result["next_act_id"] = inferred_next_act_id
                        result["next_seq_id"] = str(first_seq)
                        if reason:
                            result["reason"] = (
                                f"{reason} | fallback: inferred next_act_id/next_seq_id"
                            )
                        else:
                            result["reason"] = (
                                "fallback: inferred next_act_id/next_seq_id"
                            )
                        return result

        if not next_act_id or next_seq_id:
            return result

        normalized_next_act = normalize(next_act_id)
        inferred_seq: Optional[str] = None
        next_ctx = await self.repository.get_act_context(
            scenario_id, normalized_next_act
        )
        next_sequences = (next_ctx or {}).get("sequences", [])
        if next_sequences:
            first_seq = next_sequences[0].get("id")
            if first_seq:
                inferred_seq = str(first_seq)

        if inferred_seq:
            reason = str(result.get("reason") or "").strip()
            result["next_seq_id"] = inferred_seq
            if reason:
                result["reason"] = (
                    f"{reason} | fallback: inferred next_seq_id for next_act_id"
                )
            else:
                result["reason"] = "fallback: inferred next_seq_id for next_act_id"
            return result

        # Avoid downstream 502 in GM commit_state when transition pair is incomplete.
        result["next_act_id"] = None
        reason = str(result.get("reason") or "").strip()
        if reason:
            result["reason"] = (
                f"{reason} | fallback: dropped next_act_id without next_seq_id"
            )
        else:
            result["reason"] = "fallback: dropped next_act_id without next_seq_id"
        return result

    def _apply_transition_fallback(
        self,
        result: Dict[str, Any],
        user_input: str,
        current_seq: Dict[str, Any],
        sequences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result

        if result.get("next_act_id"):
            return result
        if result.get("next_seq_id"):
            return result

        triggers = [
            str(t).strip()
            for t in (current_seq.get("exit_triggers") or [])
            if str(t).strip()
        ]
        if not self._is_trigger_match(user_input, triggers):
            return result

        # Preserve trigger signal even when this act has no forward sequence.
        result["is_triggered"] = True
        next_seq_id = self._infer_next_sequence_id(
            current_seq_id=str(current_seq.get("id", "")),
            sequences=sequences,
        )
        if not next_seq_id:
            reason = str(result.get("reason") or "").strip()
            if reason:
                result["reason"] = (
                    f"{reason} | fallback: exit_trigger heuristic matched"
                )
            else:
                result["reason"] = "fallback: exit_trigger heuristic matched"
            return result

        reason = str(result.get("reason") or "").strip()
        result["next_seq_id"] = next_seq_id
        if reason:
            result["reason"] = f"{reason} | fallback: exit_trigger heuristic matched"
        else:
            result["reason"] = "fallback: exit_trigger heuristic matched"
        return result

    def _infer_next_sequence_id(
        self,
        current_seq_id: str,
        sequences: List[Dict[str, Any]],
    ) -> Optional[str]:
        ordered = self._ordered_sequences(sequences)
        if not current_seq_id or not ordered:
            return None

        current_idx = None
        normalized_current = self._norm_text(current_seq_id)
        for i, seq in enumerate(ordered):
            if self._norm_text(seq.get("id")) == normalized_current:
                current_idx = i
                break
        if current_idx is None:
            return None
        if current_idx + 1 >= len(ordered):
            return None
        next_id = ordered[current_idx + 1].get("id")
        return str(next_id) if next_id else None

    def _norm_text(self, val: Any) -> str:
        return str(val or "").strip().lower()

    def _seq_sort_key(self, seq_id: Any) -> tuple[int, str]:
        sid = str(seq_id or "")
        nums = re.findall(r"\d+", sid)
        return (int(nums[0]) if nums else 10**9, sid)

    def _ordered_sequences(
        self, sequences: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        return sorted(sequences or [], key=lambda s: self._seq_sort_key(s.get("id")))

    def _sequence_index(
        self, seq_id: str, sequences: List[Dict[str, Any]]
    ) -> Optional[int]:
        normalized = self._norm_text(seq_id)
        for i, seq in enumerate(self._ordered_sequences(sequences)):
            if self._norm_text(seq.get("id")) == normalized:
                return i
        return None

    def _is_terminal_sequence(
        self, seq_id: str, sequences: List[Dict[str, Any]]
    ) -> bool:
        ordered = self._ordered_sequences(sequences)
        if not ordered:
            return False
        idx = self._sequence_index(seq_id, ordered)
        return idx is not None and idx == len(ordered) - 1

    def _infer_next_act_id(self, current_act_id: str) -> Optional[str]:
        sid = str(current_act_id or "").strip().lower()
        m = re.match(r"^act-(\d+)$", sid)
        if not m:
            return None
        return f"act-{int(m.group(1)) + 1}"

    def _guard_non_forward_sequence_transition(
        self,
        result: Dict[str, Any],
        current_seq_id: str,
        sequences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result
        if result.get("next_act_id"):
            return result
        next_seq_id = result.get("next_seq_id")
        if not next_seq_id:
            return result

        cur_idx = self._sequence_index(current_seq_id, sequences)
        nxt_idx = self._sequence_index(str(next_seq_id), sequences)
        if cur_idx is None or nxt_idx is None:
            return result
        if nxt_idx > cur_idx:
            return result

        # Block backward/same-sequence jump to avoid infinite bouncing.
        result["next_seq_id"] = None
        reason = str(result.get("reason") or "").strip()
        if reason:
            result["reason"] = f"{reason} | guard: blocked non-forward next_seq_id"
        else:
            result["reason"] = "guard: blocked non-forward next_seq_id"
        return result

    def _mark_should_end_if_terminal_triggered(
        self,
        result: Dict[str, Any],
        current_seq_id: str,
        sequences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result

        result.setdefault("should_end", False)
        if result.get("next_act_id") or result.get("next_seq_id"):
            return result
        if not bool(result.get("is_triggered")):
            return result

        ordered = self._ordered_sequences(sequences)
        if not ordered:
            return result
        cur_idx = self._sequence_index(current_seq_id, ordered)
        if cur_idx is None or cur_idx != len(ordered) - 1:
            return result

        result["should_end"] = True
        reason = str(result.get("reason") or "").strip()
        if reason:
            result["reason"] = f"{reason} | terminal sequence reached: should_end"
        else:
            result["reason"] = "terminal sequence reached: should_end"
        return result

    async def _recover_act_boundary_transition(
        self,
        result: Dict[str, Any],
        scenario_id: str,
        current_act_id: str,
        current_seq_id: str,
        current_act_sequences: List[Dict[str, Any]],
        user_input: str,
        current_seq: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result
        if result.get("next_act_id") or result.get("next_seq_id"):
            return result
        if not bool(result.get("is_triggered")):
            return result
        if not self._is_terminal_sequence(current_seq_id, current_act_sequences):
            return result
        triggers = [
            str(t).strip()
            for t in (current_seq.get("exit_triggers") or [])
            if str(t).strip()
        ]
        if not self._is_trigger_match(user_input, triggers):
            return result

        inferred_next_act_id = self._infer_next_act_id(current_act_id)
        if not inferred_next_act_id:
            return result

        next_ctx = await self.repository.get_act_context(
            scenario_id, inferred_next_act_id
        )
        next_sequences = (next_ctx or {}).get("sequences", [])
        if not next_sequences:
            return result

        first_seq = next_sequences[0].get("id")
        if not first_seq:
            return result

        reason = str(result.get("reason") or "").strip()
        result["next_act_id"] = inferred_next_act_id
        result["next_seq_id"] = str(first_seq)
        result["should_end"] = False
        if reason:
            result["reason"] = f"{reason} | fallback: recovered act-boundary transition"
        else:
            result["reason"] = "fallback: recovered act-boundary transition"
        return result

    def _is_trigger_match(self, user_input: str, triggers: List[str]) -> bool:
        if not user_input or not triggers:
            return False

        def normalize_text(text: str) -> str:
            return re.sub(r"\s+", "", str(text or "")).lower()

        def tokens(text: str) -> List[str]:
            base = re.findall(r"[가-힣a-zA-Z0-9]+", str(text or "").lower())
            stopwords = {
                "그리고",
                "또는",
                "으로",
                "에서",
                "한다",
                "했다",
                "하기",
                "the",
                "and",
            }
            return [t for t in base if len(t) >= 2 and t not in stopwords]

        normalized_input = normalize_text(user_input)
        input_tokens = set(tokens(user_input))

        for trig in triggers:
            trig_norm = normalize_text(trig)
            if trig_norm and (
                trig_norm in normalized_input or normalized_input in trig_norm
            ):
                return True

            trig_tokens = tokens(trig)
            if len(trig_tokens) < 2 or not input_tokens:
                continue
            matched = sum(1 for tk in trig_tokens if tk in input_tokens)
            if matched / max(len(trig_tokens), 1) >= 0.6:
                return True
        return False
