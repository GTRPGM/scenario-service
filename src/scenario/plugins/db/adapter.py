# src/scenario/plugins/db/adapter.py

import json
from typing import Any, Dict, List, Optional
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
                    "concept": concept,
                    "summary": data.get("summary", ""),
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
                            "location_theme": seq.get("location_theme", ""),
                            "location_description": seq["location_description"],
                            "danger_min": seq.get("danger_min", 1),
                            "danger_max": seq.get("danger_max", 10),
                        }
                    ),
                )
                for ent in seq.get("entities", []):
                    await self.db.execute(
                        ent_cypher,
                        json.dumps(
                            {
                                "seq_id": seq["id"],
                                "ent_id": ent["id"],
                                "name": ent["name"],
                                "entity_category": ent["entity_category"],
                                "description": ent["description"],
                                "interaction_guide": ent["interaction_guide"],
                                "disposition": ent.get("disposition"),
                                "occupation": ent.get("occupation"),
                                "dialogue_style": ent.get("dialogue_style"),
                                "item_type": ent.get("item_type"),
                                "grade": ent.get("grade"),
                                "base_price": ent.get("base_price"),
                                "weight": ent.get("weight"),
                                "effect_value": ent.get("effect_value"),
                                "enemy_type": ent.get("enemy_type"),
                                "base_difficulty": ent.get("base_difficulty"),
                                "combat_description": ent.get("combat_description"),
                            }
                        ),
                    )

    async def list_scenarios(self) -> List[Dict[str, Any]]:
        query = self.loader.load_cypher("list_scenarios")
        rows = await self.db.fetch(query)
        return [dict(row) for row in rows]

    async def get_scenario_full_graph(self, scenario_id: UUID) -> Dict[str, Any]:
        query = self.loader.load_cypher("get_scenario_full_graph")
        params = json.dumps({"scenario_id": str(scenario_id)})
        rows = await self.db.fetch(query, params)
        if not rows:
            return {}

        acts = {}
        result = {
            "scenario_id": str(scenario_id),
            "concept": rows[0]["concept"],
            "summary": rows[0]["summary"],
            "acts": [],
        }

        for row in rows:
            a_id = row["act_id"]
            if not a_id:
                continue
            if a_id not in acts:
                acts[a_id] = {"id": a_id, "name": row["act_name"], "sequences": {}}

            s_id = row["seq_id"]
            if s_id:
                if s_id not in acts[a_id]["sequences"]:
                    acts[a_id]["sequences"][s_id] = {
                        "id": s_id,
                        "name": row["seq_name"],
                        "location": {
                            "name": row["loc_name"],
                            "theme": row["loc_theme"],
                        },
                        "entities": [],
                    }

                if row["ent_id"]:
                    acts[a_id]["sequences"][s_id]["entities"].append(
                        {
                            "id": row["ent_id"],
                            "name": row["ent_name"],
                            "category": row["ent_cat"],
                            "description": row["ent_desc"],
                            "interaction_guide": row["ent_guide"],
                        }
                    )

        # Convert nested dicts to lists
        for a_id in acts:
            acts[a_id]["sequences"] = list(acts[a_id]["sequences"].values())
        result["acts"] = list(acts.values())
        return result

    async def create_session(
        self, session_id: UUID, scenario_id: UUID, initial_act: str, initial_seq: str
    ) -> None:
        sql = self.loader.load_sql("create_session")
        await self.db.execute(
            sql, session_id, scenario_id, initial_act, initial_seq, "{}"
        )

    async def list_sessions(self) -> List[Dict[str, Any]]:
        sql = (
            "SELECT session_id, scenario_id, current_act_id, current_sequence_id, "
            "updated_at FROM session_states"
        )
        rows = await self.db.fetch(sql)
        return [dict(row) for row in rows]

    async def get_session_state(self, session_id: UUID) -> Optional[Dict[str, Any]]:
        sql = "SELECT * FROM session_states WHERE session_id = $1"
        row = await self.db.fetchrow(sql, session_id)
        return dict(row) if row else None

    async def update_session_state(
        self, session_id: UUID, act_id: str, seq_id: str, context: Dict
    ) -> None:
        sql = self.loader.load_sql("update_session_state")
        await self.db.execute(sql, act_id, seq_id, json.dumps(context), session_id)
