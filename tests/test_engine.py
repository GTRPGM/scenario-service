# tests/test_engine.py

from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_scenario_writer_graph_run():
    planner = MagicMock()
    planner.run = AsyncMock(
        return_value={
            "title": "Test",
            "acts": [{"id": "act-1", "name": "Act 1", "sequences": ["seq-1"]}],
        }
    )

    writer = MagicMock()
    writer.run = AsyncMock(return_value={"sequences": [{"id": "seq-1"}]})

    reviewer = MagicMock()
    reviewer.run = AsyncMock(return_value={"is_consistent": True, "reviews": []})

    writer_graph = ScenarioWriterGraph(
        planner=planner, writer=writer, reviewer=reviewer
    )

    result = await writer_graph.run("Fantasy concept")

    assert result["concept"] == "Fantasy concept"
    assert result["plan"]["acts"][0]["id"] == "act-1"
    assert result["content"]["sequences"][0]["id"] == "seq-1"
    assert result["is_consistent"] is True
    assert planner.run.called
    assert writer.run.called
    assert reviewer.run.called
