from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.plugins.db.adapter import PostgresScenarioAdapter


@pytest.fixture
def mock_data():
    return {
        "plan": {
            "title": "Test Scenario",
            "description": "Long Desc",
            "total_summary": "Summary",
            "difficulty": "normal",
            "genre": "fantasy",
            "tags": ["test"],
            "total_acts": 1,
            "acts": [
                {
                    "id": "act-1",
                    "name": "Act 1",
                    "goal": "Goal 1",
                    "region_name": "Region 1",
                    "description": "Desc 1",
                    "exit_criteria": "Exit 1",
                    "sequences": ["seq-1"],
                }
            ],
            "relations": [
                {
                    "from_id": "npc-1",
                    "to_id": "enemy-1",
                    "relation_type": "foe",
                    "affinity": 0,
                    "meta": {"reason": "grudge"},
                }
            ],
        },
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "Seq 1",
                    "sequence_type": "combat",
                    "location_name": "Cave",
                    "location_theme": "dark",
                    "location_description": "A dark cave",
                    "description": "Exploring...",
                    "goal": "Survive",
                    "exit_triggers": ["kill_boss"],
                    "npcs": ["npc-1"],
                    "enemies": ["enemy-1"],
                    "items": ["101"],
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_engine_aggregation_logic(mock_data):
    from uuid import uuid4

    generated_id = uuid4()
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value=generated_id)

    full_mock_return = {
        "plan": mock_data["plan"],
        "content": mock_data["content"],
        "items": [
            {
                "item_id": "101",
                "name": "Sword",
                "description": "Sharp",
                "item_type": "weapon",
                "meta": {"power": 10},
            }
        ],
        "npcs": [{"scenario_npc_id": "npc-1", "name": "N"}],
        "enemies": [
            {"scenario_enemy_id": "enemy-1", "name": "E", "dropped_items": ["101"]}
        ],
    }

    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run = AsyncMock(return_value=full_mock_return)

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("concept")

    # Final data check
    # In flat structure, sequences[0].items is a list of ID strings
    assert result["data"]["sequences"][0]["items"][0] == "101"
    assert result["scenario_id"] == str(generated_id)


@pytest.mark.asyncio
async def test_db_adapter_query_calls(mock_data):
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.fetchrow = AsyncMock(return_value={"id": str(uuid4())})

    mock_loader = MagicMock()
    mock_loader.load_cypher.side_effect = lambda name: f"QUERY_{name}"
    mock_loader.load_sql.side_effect = lambda name: f"QUERY_SQL_{name}"

    adapter = PostgresScenarioAdapter(db=mock_db, loader=mock_loader)

    # Use the new nested structure for testing the adapter
    nested_data = {
        "title": "Test",
        "summary": "summary",
        "description": "desc",
        "difficulty": "normal",
        "genre": "fantasy",
        "tags": [],
        "total_acts": 1,
        "acts": [
            {
                "id": "act-1",
                "name": "A",
                "region_name": "R",
                "region_description": "D",
                "goal": "G",
                "exit_criteria": "E",
                "sequences": ["seq-1"],
            }
        ],
        "sequences": [
            {
                "id": "seq-1",
                "name": "S",
                "description": "D",
                "goal": "G",
                "location_name": "L",
                "npcs": ["npc-1"],
                "enemies": ["enemy-1"],
                "items": ["101"],
            }
        ],
        "npcs": [{"scenario_npc_id": "npc-1", "name": "N"}],
        "enemies": [
            {"scenario_enemy_id": "enemy-1", "name": "E", "dropped_items": ["101"]}
        ],
        "items": [{"item_id": 101, "name": "I"}],
        "relations": [{"from_id": "npc-1", "to_id": "enemy-1"}],
    }

    await adapter.save_scenario("concept", nested_data)

    executed_queries = [call.args[0] for call in mock_db.execute.call_args_list]

    assert "QUERY_create_scenario_base" in executed_queries
    assert "QUERY_create_act" in executed_queries
    assert "QUERY_create_sequence" in executed_queries
    assert "QUERY_create_entity" in executed_queries
