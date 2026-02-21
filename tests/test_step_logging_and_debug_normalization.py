from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.api.v1.endpoints.generation import _run_stage
from scenario.core.engine.scenario_engine import ScenarioEngine


@pytest.mark.asyncio
async def test_run_stage_persists_step_and_request_logs_on_success():
    agent = MagicMock()
    agent.run = AsyncMock(return_value={"ok": True})

    repository = MagicMock()
    repository.save_generation_step = AsyncMock()
    repository.log_generation_request = AsyncMock()

    response = await _run_stage(
        stage="planner",
        agent=agent,
        resolved_input={"concept": "test"},
        repository=repository,
        run_id=str(uuid4()),
        endpoint="/api/v1/generation/step/planner",
        request_payload={"concept": "test"},
        retry_count=0,
    )

    assert response["status"] == "success"
    assert response["attempt_count"] == 1
    assert response["retry_count"] == 0
    assert response["db_logging_ok"] is True
    repository.save_generation_step.assert_awaited_once()
    repository.log_generation_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_stage_persists_logs_on_error():
    agent = MagicMock()
    agent.run = AsyncMock(side_effect=RuntimeError("stage failed"))

    repository = MagicMock()
    repository.save_generation_step = AsyncMock()
    repository.log_generation_request = AsyncMock()

    response = await _run_stage(
        stage="writer",
        agent=agent,
        resolved_input={"plan": {"title": "x"}},
        repository=repository,
        run_id=str(uuid4()),
        endpoint="/api/v1/generation/step/writer",
        request_payload={"plan": {"title": "x"}},
        retry_count=2,
    )

    assert response["status"] == "error"
    assert response["attempt_count"] == 3
    assert response["retry_count"] == 2
    assert "stage failed" in response["error"]
    assert response["db_logging_ok"] is True
    repository.save_generation_step.assert_awaited_once()
    repository.log_generation_request.assert_awaited_once()


@pytest.mark.asyncio
async def test_debug_inject_save_normalizes_step_outputs_automatically():
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value=uuid4())
    mock_writer = MagicMock()
    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer)

    payload = {
        "planner_output": {
            "title": "테스트",
            "acts": [{"id": "act-1", "name": "A1", "sequences": ["seq-1"]}],
            "npc_manifest": [{"id": "npc-1", "name": "N1"}],
            "enemy_manifest": [{"id": "enemy-1", "name": "E1"}],
            "item_manifest": [{"id": "item-1", "name": "I1"}],
        },
        "writer_output": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "S1",
                    "npcs": ["npc-1"],
                    "enemies": ["enemy-1"],
                    "items": ["item-1"],
                    "exit_triggers": ["x"],
                }
            ]
        },
        "relation_output": {
            "relations": [
                {
                    "from_id": "npc-1",
                    "to_id": "enemy-1",
                    "relation_type": "affinity",
                    "affinity": -50,
                    "meta": {},
                }
            ]
        },
    }

    result = await engine.save_and_inject_debug(payload, inject_to_state=False)
    assert result["status"] == "success"
    assert result["saved"] is True
    assert result["injected"] is False

    save_args = mock_repo.save_scenario.await_args.args
    saved_payload = save_args[1]
    assert saved_payload["npcs"][0]["scenario_npc_id"] == "npc-1"
    assert saved_payload["enemies"][0]["scenario_enemy_id"] == "enemy-1"
    assert saved_payload["items"][0]["scenario_item_id"] == "item-1"
    assert saved_payload["sequences"][0]["npcs"] == ["npc-1"]
