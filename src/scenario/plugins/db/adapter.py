# src/scenario/plugins/db/adapter.py

import json
from typing import Any, Dict, List
from uuid import UUID

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader
from scenario.interfaces.scenario import ScenarioRepository


class PostgresScenarioAdapter(ScenarioRepository):
    """PostgreSQL + AGE implementation of ScenarioRepository."""

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
                        "goal": act["goal"],
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

    def _clean_agtype(self, value: Any) -> Any:
        """Helper to clean up AGE agtype strings and parse JSON-like structures."""
        if isinstance(value, str):
            # AGE often returns strings wrapped in double quotes
            if value.startswith('"') and value.endswith('"'):
                val = value[1:-1]
                # Try to see if the inner value is also JSON (like a stringified dict)
                if val.startswith("{") or val.startswith("["):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        return val
                return val
            # If it's a raw JSON string without extra quotes
            if value.startswith("{") or value.startswith("["):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        return value

    async def get_scenario_full_graph(self, scenario_id: UUID) -> Dict[str, Any]:
        query = self.loader.load_cypher("get_scenario_full_graph")
        params = json.dumps({"scenario_id": str(scenario_id)})
        rows = await self.db.fetch(query, params)
        if not rows:
            return {}

        acts = {}
        first_row = rows[0]
        result = {
            "scenario_id": str(scenario_id),
            "title": self._clean_agtype(first_row.get("title", "Untitled")),
            "concept": self._clean_agtype(first_row["concept"]),
            "summary": self._clean_agtype(first_row["summary"]),
            "description": self._clean_agtype(first_row.get("description", "")),
            "difficulty": self._clean_agtype(first_row.get("difficulty", "normal")),
            "genre": self._clean_agtype(first_row.get("genre", "fantasy")),
            "tags": self._clean_agtype(first_row.get("tags", [])),
            "total_acts": first_row.get("total_acts", 0),
            "acts": [],
            "npcs": [],
            "enemies": [],
            "items": [],
            "relations": [],
        }

        entity_ids = set()

        for row in rows:
            a_id = self._clean_agtype(row["act_id"])
            if not a_id:
                continue
            if a_id not in acts:
                acts[a_id] = {
                    "id": a_id,
                    "name": self._clean_agtype(row["act_name"]),
                    "goal": self._clean_agtype(row.get("act_goal")),
                    "sequences": {},
                }

            s_id = self._clean_agtype(row["seq_id"])
            if s_id:
                if s_id not in acts[a_id]["sequences"]:
                    acts[a_id]["sequences"][s_id] = {
                        "id": s_id,
                        "name": self._clean_agtype(row["seq_name"]),
                        "description": self._clean_agtype(row.get("seq_desc")),
                        "goal": self._clean_agtype(row.get("seq_goal")),
                        "type": self._clean_agtype(row.get("seq_type")),
                        "location": {
                            "master_id": self._clean_agtype(row.get("loc_master_id")),
                            "name": self._clean_agtype(row["loc_name"]),
                            "theme": self._clean_agtype(row["loc_theme"]),
                            "description": self._clean_agtype(row.get("loc_desc")),
                        },
                        "entities": [],
                    }

                if row["ent_id"]:
                    ent_id = self._clean_agtype(row["ent_id"])
                    ent_data = {
                        "id": ent_id,
                        "master_id": self._clean_agtype(row.get("ent_master_id")),
                        "name": self._clean_agtype(row["ent_name"]),
                        "category": self._clean_agtype(row["ent_cat"]),
                        "description": self._clean_agtype(row["ent_desc"]),
                        "tags": self._clean_agtype(row.get("ent_tags", [])),
                        "state": self._clean_agtype(row.get("ent_state", {})),
                        "meta": self._clean_agtype(row.get("ent_meta", {})),
                        "dropped_items": self._clean_agtype(row.get("ent_drops", [])),
                    }
                    acts[a_id]["sequences"][s_id]["entities"].append(ent_data)

                    if ent_id not in entity_ids:
                        entity_ids.add(ent_id)
                        if ent_data["category"] == "NPC":
                            result["npcs"].append(
                                {
                                    "scenario_npc_id": ent_id,
                                    "master_id": ent_data["master_id"],
                                    "name": ent_data["name"],
                                    "description": ent_data["description"],
                                    "tags": ent_data["tags"],
                                    "state": ent_data["state"],
                                }
                            )
                        elif ent_data["category"] == "ENEMY":
                            result["enemies"].append(
                                {
                                    "scenario_enemy_id": ent_id,
                                    "master_id": ent_data["master_id"],
                                    "name": ent_data["name"],
                                    "description": ent_data["description"],
                                    "tags": ent_data["tags"],
                                    "state": ent_data["state"],
                                    "dropped_items": ent_data["dropped_items"],
                                }
                            )
                        elif ent_data["category"] == "ITEM":
                            result["items"].append(
                                {
                                    "item_id": ent_id,
                                    "master_id": ent_data["master_id"],
                                    "name": ent_data["name"],
                                    "description": ent_data["description"],
                                    "item_type": "misc",
                                    "meta": ent_data["meta"],
                                }
                            )

        # Convert nested dicts to lists
        for a_id in acts:
            acts[a_id]["sequences"] = list(acts[a_id]["sequences"].values())
        result["acts"] = list(acts.values())

        # Relations need a separate query or better optional match
        # For now, we assume the user mainly needs the inject payload.
        # Ideally, get_scenario_full_graph.cypher should also return relations
        return result
