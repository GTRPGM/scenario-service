from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine


@pytest.mark.asyncio
async def test_validate_progression_fallback_sets_next_seq_on_trigger_match():
    repo = MagicMock()
    repo.get_act_context = AsyncMock(
        return_value={
            "act": {
                "name": "무덤 입구",
                "goal": "입구 진입",
                "exit_criteria": "무덤 안으로 들어간다",
            },
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "입구",
                    "exit_triggers": ["무덤 입구로 들어선다."],
                },
                {"id": "seq-2", "name": "내부", "exit_triggers": []},
            ],
        }
    )
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": False,
            "reason": "LLM did not decide transition",
            "next_seq_id": None,
            "next_act_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-1",
        user_input="무덤 입구로 조심스럽게 들어선다.",
        validator_agent=validator,
    )

    assert result["is_triggered"] is True
    assert result["next_seq_id"] == "seq-2"
    assert "fallback" in result["reason"]


@pytest.mark.asyncio
async def test_validate_progression_fallback_preserves_llm_transition():
    repo = MagicMock()
    repo.get_act_context = AsyncMock(
        return_value={
            "act": {"name": "A1", "goal": "G", "exit_criteria": "E"},
            "sequences": [
                {"id": "seq-1", "name": "S1", "exit_triggers": ["문을 연다"]},
                {"id": "seq-2", "name": "S2", "exit_triggers": []},
            ],
        }
    )
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "llm transition",
            "next_seq_id": "seq-9",
            "next_act_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-1",
        user_input="문을 연다",
        validator_agent=validator,
    )

    assert result["next_seq_id"] == "seq-9"
    assert result["reason"] == "llm transition"
