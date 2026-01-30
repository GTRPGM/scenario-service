from uuid import uuid4

import pytest

from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.db.adapter import PostgresScenarioAdapter


@pytest.mark.asyncio
async def test_scenario_save_and_load_real_db(real_db_handler):
    loader = QueryLoader()
    adapter = PostgresScenarioAdapter(real_db_handler, loader)

    scenario_id = uuid4()
    concept = "A mysterious island"
    data = {
        "title": "The Island of Dr. Moreau",
        "summary": "Strange experiments on an island.",
        "difficulty": "hard",
        "genre": "horror",
        "tags": ["island", "science"],
        "total_acts": 1,
        "acts": [
            {
                "id": "act1",
                "name": "The Arrival",
                "goal": "Find shelter",
                "sequences": ["seq1"],
            }
        ],
        "sequences": [
            {
                "id": "seq1",
                "name": "Beach",
                "sequence_type": "Exploration",
                "description": "A sandy beach.",
                "goal": "Move inland",
                "exit_triggers": ["found_path"],
                "location_name": "Coast",
                "location_theme": "tropical",
                "location_description": "Palm trees and sand.",
                "npcs": [
                    {
                        "scenario_npc_id": "npc1",
                        "name": "Stranded Sailor",
                        "description": "He looks terrified.",
                        "state": {
                            "numeric": {"HP": 50},
                            "boolean": {"is_scared": True},
                        },
                    }
                ],
                "enemies": [],
                "items": [],
            }
        ],
        "relations": [],
    }

    await adapter.save_scenario(scenario_id, concept, data)
    graph = await adapter.get_scenario_full_graph(scenario_id)

    assert graph["scenario_id"] == str(scenario_id)
    assert graph["title"] == "The Island of Dr. Moreau"
    assert len(graph["acts"]) == 1
    assert graph["acts"][0]["id"] == "act1"

    sequences = graph["acts"][0]["sequences"]
    assert len(sequences) == 1
    assert len(sequences[0]["entities"]) == 1
    assert sequences[0]["entities"][0]["name"] == "Stranded Sailor"
    assert sequences[0]["entities"][0]["state"]["numeric"]["HP"] == 50
