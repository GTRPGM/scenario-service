import json
from typing import Any, Dict, List
from uuid import UUID

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader
from scenario.interfaces.scenario import ScenarioRepository


class PostgresScenarioAdapter(ScenarioRepository):
    def __init__(self, db: DatabaseHandler, loader: QueryLoader):
        self.db = db
        self.loader = loader

    async def save_scenario(
        self, scenario_id: UUID, concept: str, data: Dict[str, Any]
    ) -> None:
        scenario_id_str = str(scenario_id)
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
        act_cypher = self.loader.load_cypher("create_act")
        for act in data.get("acts", []):
            await self.db.execute(
                act_cypher,
                json.dumps(
                    {
                        "scenario_id": scenario_id_str,
                        "act_id": act["id"],
                        "name": act["name"],
                        "region_name": act.get("region_name", ""),
                        "region_description": act.get("region_description", ""),
                        "goal": act["goal"],
                        "exit_criteria": act.get("exit_criteria", ""),
                    }
                ),
            )
        seq_cypher = self.loader.load_cypher("create_sequence")
        ent_cypher = self.loader.load_cypher("create_entity")
        all_sequences = {s["id"]: s for s in data.get("sequences", [])}
        for act in data.get("acts", []):
            for seq_id in act.get("sequences", []):
                if seq_id not in all_sequences:
                    continue
                seq = all_sequences[seq_id]
                await self.db.execute(
                    seq_cypher,
                    json.dumps(
                        {
                            "act_id": act["id"],
                            "seq_id": seq["id"],
                            "name": seq["name"],
                            "sequence_type": seq.get("sequence_type", "Exploration"),
                            "description": seq["description"],
                            "goal": seq["goal"],
                            "exit_triggers": seq["exit_triggers"],
                            "location_name": seq["location_name"],
                            "location_master_id": seq.get("location_master_id"),
                            "location_theme": seq.get("location_theme", ""),
                            "location_description": seq["location_description"],
                            "danger_min": seq.get("danger_min", 1),
                            "danger_max": seq.get("danger_max", 10),
                        }
                    ),
                )

                for npc in seq.get("npcs", []):
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "seq_id": seq["id"],
                                "ent_id": npc["scenario_npc_id"],
                                "master_id": npc.get("master_id"),
                                "name": npc["name"],
                                "entity_category": "NPC",
                                "description": npc["description"],
                                "tags": npc.get("tags", []),
                                "state": npc.get("state", {}),
                                "meta": {},
                                "dropped_items": [],
                            }
                        ),
                    )
                for enemy in seq.get("enemies", []):
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "seq_id": seq["id"],
                                "ent_id": enemy["scenario_enemy_id"],
                                "master_id": enemy.get("master_id"),
                                "name": enemy["name"],
                                "entity_category": "ENEMY",
                                "description": enemy["description"],
                                "tags": enemy.get("tags", []),
                                "state": enemy.get("state", {}),
                                "meta": {},
                                "dropped_items": enemy.get("dropped_items", []),
                            }
                        ),
                    )
                for item in seq.get("items", []):
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "seq_id": seq["id"],
                                "ent_id": item["item_id"],
                                "master_id": item.get("master_id"),
                                "name": item["name"],
                                "entity_category": "ITEM",
                                "description": item["description"],
                                "tags": [],
                                "state": {},
                                "meta": item.get("meta", {}),
                                "dropped_items": [],
                            }
                        ),
                    )

        rel_cypher = self.loader.load_cypher("create_relation")
        for rel in data.get("relations", []):
            await self.db.execute(
                rel_cypher,
                json.dumps(
                    {
                        "from_id": rel["from_id"],
                        "to_id": rel["to_id"],
                        "relation_type": rel.get("relation_type", "neutral"),
                        "affinity": rel.get("affinity", 50),
                        "meta": rel.get("meta", {}),
                    }
                ),
            )

    async def list_scenarios(self) -> List[Dict[str, Any]]:
        query = self.loader.load_cypher("list_scenarios")
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]

    async def get_scenario_full_graph(self, scenario_id: UUID) -> Dict[str, Any]:
        query = self.loader.load_cypher("get_scenario_full_graph")
        rows = await self.db.fetch(query, json.dumps({"scenario_id": str(scenario_id)}))
        if not rows:
            return {}

        scenario: Dict[str, Any] = {}
        acts: Dict[str, Dict[str, Any]] = {}
        sequences: Dict[str, Dict[str, Any]] = {}
        entities: Dict[tuple[str, str], bool] = {}

        for row in rows:
            if not scenario:
                scenario = {
                    "scenario_id": self._clean_agtype(row["scenario_id"]),
                    "title": self._clean_agtype(row["title"]),
                    "concept": self._clean_agtype(row["concept"]),
                    "summary": self._clean_agtype(row["summary"]),
                    "description": self._clean_agtype(row["description"]),
                    "difficulty": self._clean_agtype(row["difficulty"]),
                    "genre": self._clean_agtype(row["genre"]),
                    "tags": self._clean_agtype(row["tags"]),
                    "total_acts": self._clean_agtype(row["total_acts"]),
                    "acts": [],
                }

            act_id = self._clean_agtype(row["act_id"])
            if act_id and act_id not in acts:
                acts[act_id] = {
                    "id": act_id,
                    "name": self._clean_agtype(row["act_name"]),
                    "goal": self._clean_agtype(row["act_goal"]),
                    "region_name": self._clean_agtype(row["act_region_name"]),
                    "region_description": self._clean_agtype(row["act_region_desc"]),
                    "exit_criteria": self._clean_agtype(row["act_exit"]),
                    "sequences": [],
                }
                scenario["acts"].append(acts[act_id])

            seq_id = self._clean_agtype(row["seq_id"])
            if seq_id and seq_id not in sequences:
                sequences[seq_id] = {
                    "id": seq_id,
                    "name": self._clean_agtype(row["seq_name"]),
                    "description": self._clean_agtype(row["seq_desc"]),
                    "goal": self._clean_agtype(row["seq_goal"]),
                    "sequence_type": self._clean_agtype(row["seq_type"]),
                    "location_name": self._clean_agtype(row["loc_name"]),
                    "location_theme": self._clean_agtype(row["loc_theme"]),
                    "location_description": self._clean_agtype(row["loc_desc"]),
                    "location_master_id": self._clean_agtype(row["loc_master_id"]),
                    "npcs": [],
                    "enemies": [],
                    "items": [],
                    "entities": [],
                }
                if act_id:
                    acts[act_id]["sequences"].append(sequences[seq_id])

            ent_id = self._clean_agtype(row["ent_id"])
            if ent_id and seq_id and (seq_id, ent_id) not in entities:
                entities[(seq_id, ent_id)] = True
                cat = self._clean_agtype(row["ent_cat"])
                ent_data = {
                    "name": self._clean_agtype(row["ent_name"]),
                    "description": self._clean_agtype(row["ent_desc"]),
                    "master_id": self._clean_agtype(row["ent_master_id"]),
                    "tags": self._clean_agtype(row["ent_tags"]),
                    "state": self._clean_agtype(row["ent_state"]),
                    "meta": self._clean_agtype(row["ent_meta"]),
                    "category": cat,
                }
                sequences[seq_id]["entities"].append(ent_data)
                if cat == "NPC":
                    ent_data["scenario_npc_id"] = ent_id
                    sequences[seq_id]["npcs"].append(ent_data)
                elif cat == "ENEMY":
                    ent_data["scenario_enemy_id"] = ent_id
                    ent_data["dropped_items"] = self._clean_agtype(row["ent_drops"])
                    sequences[seq_id]["enemies"].append(ent_data)
                elif cat == "ITEM":
                    ent_data["item_id"] = ent_id
                    sequences[seq_id]["items"].append(ent_data)

        return scenario

    def _clean_agtype(self, value: Any) -> Any:
        if isinstance(value, str):
            if value.startswith('"') and value.endswith('"'):
                val = value[1:-1]
                if val.startswith("{") or val.startswith("["):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        return val
                return val
            if value.startswith("{") or value.startswith("["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        return value

    async def get_act_context(self, scenario_id: UUID, act_id: str) -> Dict[str, Any]:
        full_graph = await self.get_scenario_full_graph(scenario_id)
        if not full_graph:
            return {}

        target_act = next(
            (a for a in full_graph.get("acts", []) if a["id"] == act_id), None
        )
        if not target_act:
            return {}

        return {"act": target_act, "sequences": target_act.get("sequences", [])}

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
