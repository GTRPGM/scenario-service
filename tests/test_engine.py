# tests/test_engine.py

from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_scenario_writer_graph_run():
    planner = MagicMock()
    planner.run = AsyncMock(return_value={"acts": ["act1"]})

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
