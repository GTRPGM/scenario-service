# tests/test_engine.py

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_scenario_engine_check_progression(mock_repository):
    session_id = uuid4()
    mock_repository.get_session_state.return_value = {
        "current_act_id": "act_1",
        "current_sequence_id": "seq_1",
        "conditions": ["goal1"],
    }

    engine = ScenarioEngine(repository=mock_repository, writer=MagicMock())
    result = await engine.check_progression(session_id, "hello")

    assert result["status"] == "active"
    assert result["context"]["act"] == "act_1"
    mock_repository.get_session_state.assert_called_once_with(session_id)


@pytest.mark.asyncio
async def test_scenario_writer_graph_run():
    planner = MagicMock()
    planner.run = AsyncMock(return_value={"plan": {"acts": ["act1"]}})

    writer = MagicMock()
    writer.run = AsyncMock(return_value={"content": [{"id": "seq1"}]})

    reviewer = MagicMock()
    reviewer.run = AsyncMock(return_value={"is_consistent": True, "reviews": []})

    writer_graph = ScenarioWriterGraph(
        planner=planner, writer=writer, reviewer=reviewer
    )

    result = await writer_graph.run("Fantasy concept")

    assert result["concept"] == "Fantasy concept"
    assert result["plan"]["acts"] == ["act1"]
    assert result["is_consistent"] is True
    assert planner.run.called
    assert writer.run.called
    assert reviewer.run.called
