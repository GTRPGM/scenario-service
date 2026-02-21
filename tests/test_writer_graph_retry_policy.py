from unittest.mock import MagicMock

from scenario.core.engine.writer_graph import ScenarioWriterGraph


def _graph() -> ScenarioWriterGraph:
    return ScenarioWriterGraph(
        planner=MagicMock(),
        writer=MagicMock(),
        reviewer=MagicMock(),
        plan_reviewer=MagicMock(),
        writer_reviewer=MagicMock(),
        asset_writer=MagicMock(),
        asset_reviewer=MagicMock(),
        relation_manager=MagicMock(),
    )


def test_plan_stage_falls_back_after_three_failures():
    graph = _graph()

    assert (
        graph._should_continue_plan({"plan_consistent": False, "plan_attempts": 1})
        == "continue"
    )
    assert (
        graph._should_continue_plan({"plan_consistent": False, "plan_attempts": 2})
        == "continue"
    )
    assert (
        graph._should_continue_plan({"plan_consistent": False, "plan_attempts": 3})
        == "end"
    )
    assert (
        graph._should_continue_plan({"plan_consistent": True, "plan_attempts": 3})
        == "next"
    )


def test_writer_stage_falls_back_after_three_failures():
    graph = _graph()

    assert (
        graph._should_continue_writer({"writer_consistent": False, "writer_attempts": 1})
        == "continue"
    )
    assert (
        graph._should_continue_writer({"writer_consistent": False, "writer_attempts": 2})
        == "continue"
    )
    assert (
        graph._should_continue_writer({"writer_consistent": False, "writer_attempts": 3})
        == "end"
    )
    assert (
        graph._should_continue_writer({"writer_consistent": True, "writer_attempts": 3})
        == "next"
    )


def test_asset_stage_falls_back_after_three_failures():
    graph = _graph()

    assert (
        graph._should_continue_asset({"asset_consistent": False, "asset_attempts": 1})
        == "continue"
    )
    assert (
        graph._should_continue_asset({"asset_consistent": False, "asset_attempts": 2})
        == "continue"
    )
    assert (
        graph._should_continue_asset({"asset_consistent": False, "asset_attempts": 3})
        == "end"
    )
    assert (
        graph._should_continue_asset({"asset_consistent": True, "asset_attempts": 3})
        == "next"
    )
