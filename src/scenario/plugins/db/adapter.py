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
