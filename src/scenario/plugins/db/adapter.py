import json
import logging
import re
import uuid
from typing import Any, Dict, List, Union
from uuid import UUID

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader
from scenario.interfaces.scenario import ScenarioRepository

logger = logging.getLogger(__name__)


class PostgresScenarioAdapter(ScenarioRepository):
    def __init__(self, db: DatabaseHandler, loader: QueryLoader):
        self.db = db
        self.loader = loader

    async def save_scenario(
        self,
        concept: str,
        data: Dict[str, Any],
        scenario_id: UUID | None = None,
    ) -> UUID:
        self._validate_payload_references(data)
        print(f"💾 [DB] Starting save_scenario for: {data.get('title')}")

        if scenario_id is None:
            uuid_row = await self.db.fetchrow(self.loader.load_sql("generate_uuid"))
            scenario_id = uuid_row["id"]
        scenario_id_str = str(scenario_id)

        await self.db.execute(
            self.loader.load_sql("insert_scenario_master"),
            scenario_id,
            data.get("title", "Untitled"),
            concept,
        )
        print(f"✅ [DB] SQL Master entry created: {scenario_id_str}")

        await self.db.execute(
            self.loader.load_cypher("create_scenario_base"),
            json.dumps(
                {
                    "scenario_id": scenario_id_str,
                    "title": data.get("title", "Untitled"),
                    "concept": concept,
                    "summary": data.get("summary", ""),
                    "description": data.get("description", ""),
                    "difficulty": data.get("difficulty", "normal"),
                    "genre": data.get("genre", "fantasy"),
                    "tags": data.get("tags", []),
                    "total_acts": data.get("total_acts", 1),
                }
            ),
        )
        print("✅ [DB] Scenario Base Node created.")

        act_cypher = self.loader.load_cypher("create_act")
        for act in data.get("acts", []):
            await self.db.execute(
                act_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "act_id": act.get("id", ""),
                        "name": act.get("name", "Untitled Act"),
                        "region_name": act.get("region_name", ""),
                        "region_description": act.get("description")
                        or act.get("region_description", ""),
                        "goal": act.get("goal", ""),
                        "exit_criteria": act.get("exit_criteria", ""),
                    }
                ),
            )
        print(f"✅ [DB] {len(data.get('acts', []))} Acts created.")

        seq_cypher = self.loader.load_cypher("create_sequence")
        loc_cypher = self.loader.load_cypher("link_location")
        all_seq_data = {s.get("id"): s for s in data.get("sequences", [])}

        async def _create_sequence_for_act(act_id: str, seq: Dict[str, Any]) -> None:
            seq_metadata = (
                seq.get("metadata") if isinstance(seq.get("metadata"), dict) else {}
            )
            seq_type = (
                seq.get("sequence_type")
                or seq_metadata.get("sequence_type")
                or "Exploration"
            )
            await self.db.execute(
                seq_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "act_id": act_id,
                        "seq_id": seq.get("id"),
                        "name": seq.get("name", "Untitled Sequence"),
                        "sequence_type": seq_type,
                        "description": seq.get("description", ""),
                        "goal": seq.get("goal", ""),
                        "exit_triggers": seq.get("exit_triggers", []),
                    }
                ),
            )
            await self.db.execute(
                loc_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "seq_id": seq.get("id"),
                        "location_master_id": seq.get("location_master_id"),
                        "location_name": seq.get("location_name", ""),
                        "location_theme": seq.get("location_theme", ""),
                        "location_description": seq.get("location_description", ""),
                        "danger_min": seq.get("danger_min", 1),
                        "danger_max": seq.get("danger_max", 10),
                    }
                ),
            )

        seq_count = 0
        placed_seq_ids = set()
        for act in data.get("acts", []):
            for seq_id in act.get("sequences", []):
                if seq_id not in all_seq_data:
                    continue
                seq = all_seq_data[seq_id]
                await _create_sequence_for_act(act.get("id"), seq)
                seq_count += 1
                placed_seq_ids.add(str(seq.get("id")))

        # LLM 출력 불안정으로 Act->Sequence 참조가 비어도 시퀀스는 반드시 저장한다.
        if all_seq_data:
            fallback_act_id = (data.get("acts") or [{}])[0].get("id") or "act-1"
            for seq in data.get("sequences", []):
                seq_id = str(seq.get("id"))
                if seq_id in placed_seq_ids:
                    continue
                await _create_sequence_for_act(fallback_act_id, seq)
                seq_count += 1

        print(f"✅ [DB] {seq_count} Sequences & Locations created.")

        ent_cypher = self.loader.load_cypher("create_entity")
        npc_map = {str(n["scenario_npc_id"]): n for n in data.get("npcs", [])}
        enemy_map = {str(e["scenario_enemy_id"]): e for e in data.get("enemies", [])}
        item_map = {
            str(i.get("scenario_item_id", i.get("item_id"))): i
            for i in data.get("items", [])
        }

        ent_count = 0
        for seq in data.get("sequences", []):
            seq_id = seq["id"]
            for n_id in seq.get("npcs", []):
                if str(n_id) in npc_map:
                    n = npc_map[str(n_id)]
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "scenario_id": scenario_id_str,
                                "seq_id": seq_id,
                                "ent_id": n["scenario_npc_id"],
                                "master_id": n.get("master_id") or n.get("rule_id"),
                                "name": n["name"],
                                "entity_category": "NPC",
                                "description": n.get("description", ""),
                                "tags": n.get("tags", []),
                                "state": n.get("state", {}),
                                "meta": {},
                                "dropped_items": [],
                            }
                        ),
                    )
                    ent_count += 1
            for e_id in seq.get("enemies", []):
                if str(e_id) in enemy_map:
                    e = enemy_map[str(e_id)]
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "scenario_id": scenario_id_str,
                                "seq_id": seq_id,
                                "ent_id": e["scenario_enemy_id"],
                                "master_id": e.get("master_id") or e.get("rule_id"),
                                "name": e["name"],
                                "entity_category": "ENEMY",
                                "description": e.get("description", ""),
                                "tags": e.get("tags", []),
                                "state": e.get("state", {}),
                                "meta": {},
                                "dropped_items": [
                                    str(i) for i in e.get("dropped_items", [])
                                ],
                            }
                        ),
                    )
                    ent_count += 1
            for i_id in seq.get("items", []):
                if str(i_id) in item_map:
                    i = item_map[str(i_id)]
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "scenario_id": scenario_id_str,
                                "seq_id": seq_id,
                                "ent_id": str(
                                    i.get("scenario_item_id", i.get("item_id"))
                                ),
                                "master_id": i.get("rule_id", i.get("master_id")),
                                "name": i["name"],
                                "entity_category": "ITEM",
                                "description": i.get("description", ""),
                                "tags": [],
                                "state": {},
                                "meta": i.get("meta", {}),
                                "dropped_items": [],
                            }
                        ),
                    )
                    ent_count += 1

        # Unplaced Entities 처리 추가
        all_npc_ids = {str(n["scenario_npc_id"]) for n in data.get("npcs", [])}
        linked_npc_ids = set()
        all_enemy_ids = {str(e["scenario_enemy_id"]) for e in data.get("enemies", [])}
        linked_enemy_ids = set()
        all_item_ids = {
            str(i.get("scenario_item_id", i.get("item_id")))
            for i in data.get("items", [])
        }
        linked_item_ids = set()

        for seq in data.get("sequences", []):
            for n_id in seq.get("npcs", []):
                linked_npc_ids.add(str(n_id))
            for e_id in seq.get("enemies", []):
                linked_enemy_ids.add(str(e_id))
            for i_id in seq.get("items", []):
                linked_item_ids.add(str(i_id))

        # Unplaced NPCs
        remaining_npc_ids = all_npc_ids - linked_npc_ids
        npc_cypher = self.loader.load_cypher("create_unplaced_npc")
        for n_id in remaining_npc_ids:
            n = npc_map[n_id]
            await self.db.execute(
                npc_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "ent_id": n["scenario_npc_id"],
                        "master_id": n.get("master_id") or n.get("rule_id"),
                        "name": n["name"],
                        "description": n.get("description", ""),
                        "tags": n.get("tags", []),
                        "state": n.get("state", {}),
                    }
                ),
            )
            ent_count += 1

        # Unplaced Enemies
        remaining_enemy_ids = all_enemy_ids - linked_enemy_ids
        enemy_cypher = self.loader.load_cypher("create_unplaced_enemy")
        for e_id in remaining_enemy_ids:
            e = enemy_map[e_id]
            await self.db.execute(
                enemy_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "ent_id": e["scenario_enemy_id"],
                        "master_id": e.get("master_id") or e.get("rule_id"),
                        "name": e["name"],
                        "description": e.get("description", ""),
                        "tags": e.get("tags", []),
                        "state": e.get("state", {}),
                        "dropped_items": [str(i) for i in e.get("dropped_items", [])],
                    }
                ),
            )
            ent_count += 1

        # Unplaced Items
        remaining_item_ids = all_item_ids - linked_item_ids
        item_cypher = self.loader.load_cypher("create_unplaced_item")
        for i_id in remaining_item_ids:
            i = item_map[i_id]
            await self.db.execute(
                item_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "ent_id": str(i.get("scenario_item_id", i.get("item_id"))),
                        "master_id": i.get("rule_id", i.get("master_id")),
                        "name": i["name"],
                        "description": i.get("description", ""),
                        "meta": i.get("meta", {}),
                    }
                ),
            )
            ent_count += 1

        print(f"✅ [DB] {ent_count} Total Entities created (including unplaced).")

        rel_cypher = self.loader.load_cypher("create_relation")
        for rel in data.get("relations", []):
            await self.db.execute(
                rel_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "from_id": str(rel["from_id"]),
                        "to_id": str(rel["to_id"]),
                        "relation_type": rel.get("relation_type", "neutral"),
                        "affinity": rel.get("affinity", 50),
                        "meta": rel.get("meta", {}),
                    }
                ),
            )
        print(f"✅ [DB] {len(data.get('relations', []))} Relations created.")
        return scenario_id

    async def _delete_scenario_by_id(self, scenario_id: UUID | str) -> None:
        sid = str(scenario_id)
        await self.db.execute(
            self.loader.load_cypher("delete_scenario_nodes"),
            json.dumps({"scenario_id": sid}),
        )
        await self.db.execute(
            self.loader.load_sql("delete_scenario_master"),
            sid,
        )

    async def save_or_replace_scenario_by_concept(
        self, concept: str, data: Dict[str, Any]
    ) -> UUID:
        rows = await self.db.fetch(
            self.loader.load_sql("get_scenario_ids_by_concept"),
            concept,
        )
        if not rows:
            return await self.save_scenario(concept, data)

        ordered_ids = [row["id"] for row in rows]
        reuse_id = ordered_ids[0]
        for sid in ordered_ids:
            await self._delete_scenario_by_id(sid)
        return await self.save_scenario(concept, data, scenario_id=reuse_id)

    def _validate_payload_references(self, data: Dict[str, Any]) -> None:
        acts = data.get("acts", []) or []
        sequences = data.get("sequences", []) or []
        npcs = data.get("npcs", []) or []
        enemies = data.get("enemies", []) or []
        items = data.get("items", []) or []
        relations = data.get("relations", []) or []

        seq_ids = {str(s.get("id")) for s in sequences}
        npc_ids = {str(n.get("scenario_npc_id")) for n in npcs}
        enemy_ids = {str(e.get("scenario_enemy_id")) for e in enemies}
        item_ids = {
            str(i.get("scenario_item_id", i.get("item_id")))
            for i in items
            if i.get("scenario_item_id") is not None or i.get("item_id") is not None
        }
        entity_ids = npc_ids | enemy_ids | item_ids

        for act in acts:
            for seq_id in act.get("sequences", []) or []:
                if str(seq_id) not in seq_ids:
                    raise ValueError(
                        f"Invalid act->sequence reference: {act.get('id')} -> {seq_id}"
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

    def _get_props(self, val: Any) -> Dict[str, Any]:
        """Safely extract properties and merge with node ID."""
        data = self._clean_agtype(val)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if isinstance(data, dict):
            props = data.get("properties", {}).copy()
            # Ensure 'id' is present in props (fallback to node metadata id)
            if "id" not in props and "id" in data:
                props["id"] = data["id"]
            return props
        return {}

    async def get_scenario_full_graph(
        self, scenario_id: Union[UUID, str]
    ) -> Dict[str, Any]:
        print(f"🔍 [DB] Retrieving full graph for: {scenario_id}")

        # 1. Try lookup by internal ID or state_manager_id in SQL
        # Convert to UUID object only if it looks like one to avoid asyncpg error
        scenario_uuid = None
        if isinstance(scenario_id, UUID):
            scenario_uuid = scenario_id
        else:
            try:
                scenario_uuid = UUID(scenario_id)
            except (ValueError, TypeError):
                scenario_uuid = None

        scenario_query = self.loader.load_sql("get_scenario_master")
        sql_row = await self.db.fetchrow(
            scenario_query,
            scenario_uuid,
            str(scenario_id),
        )

        # Use the actual internal ID for the graph query
        internal_id = str(sql_row["id"]) if sql_row else str(scenario_id)
        params = json.dumps({"scenario_id": internal_id})

        base_query = self.loader.load_cypher("get_scenario_base_node")
        base_row = await self.db.fetchrow(base_query, params)
        if not base_row:
            return {}

        s_node = self._get_props(base_row["s"])

        scenario = {
            "scenario_id": str(internal_id),
            "state_manager_id": sql_row["state_manager_id"]
            if sql_row
            else s_node.get("state_manager_id"),
            "title": sql_row["title"] if sql_row else s_node.get("title", "Untitled"),
            "concept": sql_row["concept"] if sql_row else s_node.get("concept", ""),
            "summary": s_node.get("summary", ""),
            "description": s_node.get("description", ""),
            "difficulty": s_node.get("difficulty", "normal"),
            "genre": s_node.get("genre", "fantasy"),
            "tags": s_node.get("tags", []),
            "total_acts": s_node.get("total_acts", 1),
            "acts": [],
            "sequences": [],
            "npcs": [],
            "enemies": [],
            "items": [],
            "relations": [],
        }

        # 2. Fetch Acts (Independent Query)
        act_query = self.loader.load_cypher("get_scenario_acts")
        act_rows, act_map = await self.db.fetch(act_query, params), {}
        for r in act_rows:
            a_id = self._clean_agtype(r["id"])
            a = self._get_props(r["a"])
            act_data = {
                "id": a_id,
                "name": a.get("name", ""),
                "goal": a.get("goal", ""),
                "region_name": a.get("region_name", ""),
                "region_description": a.get("region_description", ""),
                "exit_criteria": a.get("exit_criteria", ""),
                "sequences": [],
            }
            act_map[a_id] = act_data
            scenario["acts"].append(act_data)

        # 3. Fetch Sequences (Independent Query)
        seq_query = self.loader.load_cypher("get_scenario_sequences")
        seq_rows, seq_map = await self.db.fetch(seq_query, params), {}
        for r in seq_rows:
            a_id = self._clean_agtype(r["act_id"])
            s_id = self._clean_agtype(r["seq_id"])
            s = self._get_props(r["seq"])
            loc_props = self._get_props(r["loc"]) if r["loc"] else {}

            # Ensure exit_triggers is a list
            # (Apache AGE lists come back as JSON strings via _clean_agtype)
            raw_triggers = s.get("exit_triggers", [])
            if isinstance(raw_triggers, str):
                try:
                    raw_triggers = json.loads(raw_triggers)
                except json.JSONDecodeError:
                    raw_triggers = [raw_triggers] if raw_triggers else []

            seq_data = {
                "id": s_id,
                "name": s.get("name", ""),
                "description": s.get("description", ""),
                "goal": s.get("goal", ""),
                "sequence_type": s.get("sequence_type", "Exploration"),
                "exit_triggers": raw_triggers if isinstance(raw_triggers, list) else [],
                "location_name": loc_props.get("name", "Unknown"),
                "location_master_id": loc_props.get("id"),
                "location_theme": loc_props.get("theme", ""),
                "location_description": loc_props.get("description", ""),
                "danger_min": loc_props.get("danger_min", 1),
                "danger_max": loc_props.get("danger_max", 10),
                "npcs": [],
                "enemies": [],
                "items": [],
            }
            seq_map[s_id] = seq_data
            scenario["sequences"].append(seq_data)
            if a_id in act_map:
                act_map[a_id]["sequences"].append(s_id)

        # 4. Fetch Entities (Independent Query)
        ent_query = self.loader.load_cypher("get_scenario_entities")
        ent_rows, npc_cat, enemy_cat, item_cat = (
            await self.db.fetch(ent_query, params),
            {},
            {},
            {},
        )
        for r in ent_rows:
            # Process placed entities
            if r["e"]:
                s_id = self._clean_agtype(r["seq_id"])
                e_id = self._clean_agtype(r["ent_id"])
                e = self._get_props(r["e"])
                cat = e.get("category")
                ent_common = {
                    "name": e.get("name", ""),
                    "description": e.get("description", ""),
                    "master_id": e.get("master_id"),
                    "tags": e.get("tags", []),
                    "state": e.get("state", {}),
                    "meta": e.get("meta", {}),
                }

                if cat == "NPC":
                    ent_common["scenario_npc_id"] = e_id
                    npc_cat[e_id] = ent_common
                    if s_id in seq_map and e_id not in seq_map[s_id]["npcs"]:
                        seq_map[s_id]["npcs"].append(e_id)
                elif cat == "ENEMY":
                    ent_common["scenario_enemy_id"] = e_id
                    ent_common["dropped_items"] = [
                        self._extract_int_id(i) for i in e.get("dropped_items", [])
                    ]
                    enemy_cat[e_id] = ent_common
                    if s_id in seq_map and e_id not in seq_map[s_id]["enemies"]:
                        seq_map[s_id]["enemies"].append(e_id)
                elif cat == "ITEM":
                    ent_common["scenario_item_id"] = e_id
                    item_cat[e_id] = ent_common
                    if s_id in seq_map and e_id not in seq_map[s_id]["items"]:
                        seq_map[s_id]["items"].append(e_id)

            # Process unplaced entities
            if r["ue"]:
                ue_id = self._clean_agtype(r["uent_id"])
                ue = self._get_props(r["ue"])
                cat = ue.get("category")
                ent_common = {
                    "name": ue.get("name", ""),
                    "description": ue.get("description", ""),
                    "master_id": ue.get("master_id"),
                    "tags": ue.get("tags", []),
                    "state": ue.get("state", {}),
                    "meta": ue.get("meta", {}),
                }
                if cat == "NPC":
                    ent_common["scenario_npc_id"] = ue_id
                    npc_cat[ue_id] = ent_common
                elif cat == "ENEMY":
                    ent_common["scenario_enemy_id"] = ue_id
                    ent_common["dropped_items"] = [
                        self._extract_int_id(i) for i in ue.get("dropped_items", [])
                    ]
                    enemy_cat[ue_id] = ent_common
                elif cat == "ITEM":
                    ent_common["scenario_item_id"] = ue_id
                    item_cat[ue_id] = ent_common

        scenario["npcs"], scenario["enemies"], scenario["items"] = (
            list(npc_cat.values()),
            list(enemy_cat.values()),
            list(item_cat.values()),
        )

        rel_query = self.loader.load_cypher("get_scenario_relations")
        rel_rows = await self.db.fetch(rel_query, params)
        for r in rel_rows:
            f_id, t_id = (
                self._clean_agtype(r["from_id"]),
                self._clean_agtype(r["to_id"]),
            )
            scenario["relations"].append(
                {
                    "from_id": f_id,
                    "to_id": t_id,
                    "relation_type": self._clean_agtype(r["rel_type"]),
                    "affinity": self._clean_agtype(r["affinity"]) or 50,
                    "meta": self._clean_agtype(r["meta"]) or {},
                }
            )

        print(f"✅ [DB] Full graph retrieval complete for: {scenario_id}")
        return scenario

    def _extract_int_id(self, val: Any) -> int:
        import re

        nums = re.findall(r"\d+", str(val))
        return int(nums[0]) if nums else 0

    def _clean_agtype(self, value: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value

        # Remove Apache AGE type suffixes if present
        for suffix in ["::vertex", "::edge", "::path", "::agtype"]:
            if value.endswith(suffix):
                value = value[: -len(suffix)]
                break

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def create_generation_run(self, concept: str | None) -> UUID:
        uuid_row = await self.db.fetchrow(self.loader.load_sql("generate_uuid"))
        run_id = uuid_row["id"]
        await self.db.execute(
            self.loader.load_sql("insert_generation_run"),
            run_id,
            concept,
        )
        return run_id

    async def count_generation_requests_for_stage(
        self, run_id: UUID | str, stage: str
    ) -> int:
        rid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
        row = await self.db.fetchrow(
            self.loader.load_sql("count_generation_requests_for_stage"),
            rid,
            stage,
        )
        return int(row["cnt"]) if row else 0

    async def save_generation_step(
        self,
        *,
        run_id: UUID | str,
        checkpoint_id: str,
        stage: str,
        status: str,
        attempt_count: int,
        resolved_input: Dict[str, Any],
        result: Dict[str, Any] | None,
        error: str | None,
    ) -> None:
        rid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))
        await self.db.execute(
            self.loader.load_sql("insert_generation_step"),
            rid,
            checkpoint_id,
            stage,
            status,
            attempt_count,
            json.dumps(resolved_input, ensure_ascii=False, default=str),
            json.dumps(result, ensure_ascii=False, default=str)
            if result is not None
            else None,
            error,
        )

    async def log_generation_request(
        self,
        *,
        run_id: UUID | str | None,
        stage: str,
        endpoint: str,
        request_payload: Dict[str, Any],
        response_payload: Dict[str, Any] | None,
        status: str,
        retry_count: int,
        error: str | None,
    ) -> UUID:
        request_id = uuid.uuid4()
        rid: UUID | None
        if run_id is None:
            rid = None
        elif isinstance(run_id, UUID):
            rid = run_id
        else:
            rid = UUID(str(run_id))

        await self.db.execute(
            self.loader.load_sql("insert_generation_request_log"),
            request_id,
            rid,
            stage,
            endpoint,
            json.dumps(request_payload, ensure_ascii=False, default=str),
            json.dumps(response_payload, ensure_ascii=False, default=str)
            if response_payload is not None
            else None,
            status,
            retry_count,
            error,
        )
        return request_id

    async def get_generation_run_report(self, run_id: UUID | str) -> Dict[str, Any]:
        rid = run_id if isinstance(run_id, UUID) else UUID(str(run_id))

        run_row = await self.db.fetchrow(self.loader.load_sql("get_generation_run"), rid)
        if not run_row:
            return {}

        step_rows = await self.db.fetch(
            self.loader.load_sql("get_generation_steps_by_run"),
            rid,
        )
        log_rows = await self.db.fetch(
            self.loader.load_sql("get_generation_logs_by_run"),
            rid,
        )

        return {
            "run": dict(run_row),
            "steps": [dict(r) for r in step_rows],
            "logs": [dict(r) for r in log_rows],
        }

    async def list_scenarios(self) -> List[Dict[str, Any]]:
        query = self.loader.load_cypher("list_scenarios")
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]

    async def update_external_id(
        self, scenario_id: UUID, external_id: str, provider: str = "state_manager"
    ) -> None:
        if provider == "state_manager":
            await self.db.execute(
                self.loader.load_sql("update_scenario_state_manager_id"),
                external_id,
                scenario_id,
            )

        # Load and format the Cypher query dynamically
        cypher_template = self.loader.load_cypher("update_scenario_external_id")
        query = cypher_template.format(provider=provider)

        await self.db.execute(
            query,
            json.dumps({"scenario_id": str(scenario_id), "external_id": external_id}),
        )
        logger.info(
            f"Linked scenario {scenario_id} to {provider} "
            f"ID: {external_id} (SQL & Graph)"
        )

    async def get_act_context(
        self, scenario_id: Union[UUID, str], act_id: str
    ) -> Dict[str, Any]:
        full_graph = await self.get_scenario_full_graph(scenario_id)
        if not full_graph:
            return {}
        target_act = next(
            (a for a in full_graph.get("acts", []) if a["id"] == act_id), None
        )
        if not target_act:
            return {}

        # Filter full sequence objects that belong to this act
        act_seq_ids = target_act.get("sequences", [])
        seq_map = {str(s.get("id")): s for s in full_graph.get("sequences", [])}
        act_sequences = [
            seq_map[str(seq_id)] for seq_id in act_seq_ids if str(seq_id) in seq_map
        ]

        # Keep deterministic progression order (seq-1, seq-2, ...), even if source rows
        # are returned out-of-order.
        def _seq_sort_key(seq: Dict[str, Any]) -> tuple[int, str]:
            seq_id = str(seq.get("id", ""))
            nums = re.findall(r"\d+", seq_id)
            return (int(nums[0]) if nums else 10**9, seq_id)

        act_sequences = sorted(act_sequences, key=_seq_sort_key)

        return {"act": target_act, "sequences": act_sequences}

    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, data: Dict
    ) -> None:
        sql = self.loader.load_sql("update_session_state")
        await self.db.execute(sql, act_id, seq_id, json.dumps(data), session_id)

    async def get_session_state(self, session_id: UUID) -> Dict[str, Any]:
        sql = self.loader.load_sql("get_session_state")
        row = await self.db.fetchrow(sql, str(session_id))
        if not row:
            return {}
        row_dict = dict(row)
        if isinstance(row_dict.get("context_data"), str):
            try:
                row_dict["context_data"] = json.loads(row_dict["context_data"])
            except json.JSONDecodeError:
                pass
        return row_dict
