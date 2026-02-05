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
        }
    )

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("Test Concept")

    assert result["status"] == "success"
    data = result["data"]

    # Assert Flat Structure (references only)
    assert data["sequences"][0]["items"][0] == "item-101"
    assert data["sequences"][0]["npcs"][0] == "npc-1"
