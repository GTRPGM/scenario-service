# tests/test_injection_schema.py

from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_generate_scenario_aggregation():
    # Mock Repository
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock()

    # Mock Planner and Writer output
    mock_plan = {
        "title": "Test Title",
        "description": "Test Desc",
        "total_summary": "Summary",
        "difficulty": "hard",
        "genre": "horror",
        "tags": ["tag1"],
        "total_acts": 2,
        "acts": [{"id": "act1", "sequences": ["seq1"]}],
    }

    mock_content = {
        "sequences": [
            {
                "id": "seq1",
                "npcs": [{"scenario_npc_id": "npc1", "name": "NPC 1"}],
                "enemies": [{"scenario_enemy_id": "enemy1", "name": "Enemy 1"}],
                "items": [{"item_id": "item1", "name": "Item 1"}],
            }
        ]
    }

    # Mock Graph
    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run = AsyncMock(
        return_value={"plan": mock_plan, "content": mock_content}
    )

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("Test Concept")

    assert result["status"] == "success"
    data = result["data"]
    assert data["title"] == "Test Title"
    assert len(data["npcs"]) == 1
    assert data["npcs"][0]["scenario_npc_id"] == "npc1"
    assert len(data["enemies"]) == 1
    assert len(data["items"]) == 1

    # Check if repository was called with correct data
    mock_repo.save_scenario.assert_called_once()
    args, _ = mock_repo.save_scenario.call_args
    # args[0] is scenario_id, args[1] is concept, args[2] is data
    assert args[1] == "Test Concept"
    assert args[2]["npcs"] == [{"scenario_npc_id": "npc1", "name": "NPC 1"}]
