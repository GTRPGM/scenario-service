from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_generate_scenario_aggregation():
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock()

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
                "region_description": "Region 1",
                "goal": "Goal 1",
                "exit_criteria": "Exit 1",
                "sequences": ["seq1"],
            }
        ],
        "relations": [],
    }

    mock_content = {
        "sequences": [
            {
                "id": "seq1",
                "name": "Sequence 1",
                "sequence_type": "Exploration",
                "location_name": "Location 1",
                "description": "Desc 1",
                "goal": "Goal 1",
                "exit_triggers": ["Exit 1"],
                "npcs": [{"scenario_npc_id": "npc1", "name": "NPC 1"}],
                "enemies": [{"scenario_enemy_id": "enemy1", "name": "Enemy 1"}],
                "items": [{"item_id": "item1", "name": "Item 1"}],
            }
        ]
    }

    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run = AsyncMock(
        return_value={"plan": mock_plan, "content": mock_content}
    )

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("Test Concept")

    assert result["status"] == "success"
    data = result["data"]
    assert data["title"] == "Test Title"
    assert len(data["acts"]) == 1
    assert data["acts"][0]["id"] == "act1"
    assert data["acts"][0]["sequences"] == ["seq1"]

    assert len(data["sequences"]) == 1
    assert data["sequences"][0]["id"] == "seq1"
    assert data["sequences"][0]["npcs"] == ["npc1"]

    assert len(data["npcs"]) == 1
    assert data["npcs"][0]["scenario_npc_id"] == "npc1"

    # Check if repository was called with correct data
    call_args = mock_repo.save_scenario.call_args
    assert call_args is not None
    # args[2] is data
    saved_data = call_args[0][2]
    assert saved_data["title"] == "Test Title"
    assert "npcs" in saved_data
    assert len(saved_data["npcs"]) == 1
