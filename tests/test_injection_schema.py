from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_generate_scenario_aggregation():
    from uuid import uuid4

    generated_id = uuid4()
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value=generated_id)

    mock_plan = {
        "title": "Test Title",
        "description": "Test Desc",
        "total_summary": "Summary",
        "difficulty": "hard",
        "genre": "horror",
        "tags": ["tag1"],
        "total_acts": 2,
        "acts": [
            {
                "id": "act1",
                "name": "Act 1",
                "region_name": "Region 1",
                "description": "Region 1 Desc",
                "goal": "Goal 1",
                "exit_criteria": "Exit 1",
                "sequences": ["seq1"],
            }
        ],
        "relations": [
            {
                "from_id": "npc1",
                "to_id": "999",
                "relation_type": "소유",
                "affinity": 0,
                "meta": {},
            }
        ],
    }

    mock_item_catalog = [
        {
            "item_id": 999,
            "name": "Item 1",
            "description": "D",
            "item_type": "misc",
            "meta": {},
        }
    ]
    mock_npc_catalog = [
        {
            "scenario_npc_id": "npc1",
            "name": "NPC 1",
            "description": "D",
            "state": {"numeric": {"HP": 10}, "boolean": {}},
        }
    ]

    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run = AsyncMock(
        return_value={
            "plan": mock_plan,
            "content": {
                "sequences": [
                    {
                        "id": "seq1",
                        "name": "Sequence 1",
                        "sequence_type": "Exploration",
                        "location_name": "Location 1",
                        "location_theme": "Theme 1",
                        "location_description": "Loc Desc 1",
                        "description": "Desc 1",
                        "goal": "Goal 1",
                        "exit_triggers": ["Exit 1"],
                        "npcs": ["npc1"],
                        "enemies": [],
                        "items": ["999"],
                    }
                ]
            },
            "items": mock_item_catalog,
            "npcs": mock_npc_catalog,
            "enemies": [],
            "is_consistent": True,
        }
    )
    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("Test Concept")

    assert result["status"] == "success"
    data = result["data"]

    # Assert Flat Structure (references only)
    assert data["sequences"][0]["items"][0] == "101"
    assert data["sequences"][0]["npcs"][0] == "npc-1"


def test_to_state_payload_alignment():
    engine = ScenarioEngine(repository=MagicMock(), writer=MagicMock())

    internal_data = {
        "title": "Inject Contract",
        "description": "State aligned payload",
        "acts": [
            {
                "id": "act-1",
                "name": "Act 1",
                "region_description": "Region desc",
                "exit_criteria": "Leave",
                "sequences": ["seq-1"],
            }
        ],
        "sequences": [
            {
                "id": "seq-1",
                "name": "Start",
                "location_name": "Village",
                "description": "Desc",
                "goal": "Goal",
                "exit_triggers": ["done"],
                "metadata": {"sequence_type": "NEGOTIATION"},
                "npcs": ["npc-1"],
                "enemies": ["enemy-1"],
                "items": ["101"],
            }
        ],
        "npcs": [
            {
                "scenario_npc_id": "npc-1",
                "master_id": "1001",
                "name": "Guide",
            }
        ],
        "enemies": [
            {
                "scenario_enemy_id": "enemy-1",
                "master_id": "2001",
                "name": "Wolf",
            }
        ],
        "items": [
            {
                "item_id": 101,
                "master_id": "3001",
                "name": "Rope",
            }
        ],
        "relations": [
            {"from_id": "npc-1", "to_id": "enemy-1", "relation_type": "hostile"},
            {"from_id": "enemy-1", "to_id": "101", "relation_type": "ownership"},
        ],
    }

    payload = engine._to_state_injection_payload(internal_data)

    assert payload["items"][0]["scenario_item_id"] == "101"
    assert payload["items"][0]["rule_id"] == 3001
    assert payload["npcs"][0]["rule_id"] == 1001
    assert payload["enemies"][0]["rule_id"] == 2001
    assert len(payload["relations"]) == 2

    # Verify relations matching new types
    own_rel = next(r for r in payload["relations"] if r["relation_type"] == "ownership")
    assert own_rel["from_id"] == "enemy-1"
    assert own_rel["to_id"] == "101"
