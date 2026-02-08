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


@pytest.mark.asyncio
async def test_validate_progression_infers_next_seq_when_next_act_only():
    repo = MagicMock()

    async def _get_act_context(scenario_id: str, act_id: str):
        if act_id == "act-1":
            return {
                "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
                "sequences": [{"id": "seq-1", "name": "S1", "exit_triggers": []}],
            }
        if act_id == "act-2":
            return {
                "act": {"name": "A2", "goal": "G2", "exit_criteria": "E2"},
                "sequences": [{"id": "seq-2", "name": "S2", "exit_triggers": []}],
            }
        return None

    repo.get_act_context = AsyncMock(side_effect=_get_act_context)
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "advance act",
            "next_act_id": "act-2",
            "next_seq_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-1",
        user_input="다음 막으로 진행한다",
        validator_agent=validator,
    )

    assert result["next_act_id"] == "act-2"
    assert result["next_seq_id"] == "seq-2"
    assert "inferred next_seq_id" in result["reason"]


@pytest.mark.asyncio
async def test_validate_progression_drops_next_act_when_pair_cannot_be_inferred():
    repo = MagicMock()

    async def _get_act_context(scenario_id: str, act_id: str):
        if act_id == "act-1":
            return {
                "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
                "sequences": [{"id": "seq-1", "name": "S1", "exit_triggers": []}],
            }
        return None

    repo.get_act_context = AsyncMock(side_effect=_get_act_context)
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "bad transition",
            "next_act_id": "act-99",
            "next_seq_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-1",
        user_input="다음 막으로 진행한다",
        validator_agent=validator,
    )

    assert result["next_act_id"] is None
    assert result.get("next_seq_id") is None
    assert "dropped next_act_id" in result["reason"]


@pytest.mark.asyncio
async def test_validate_progression_blocks_backward_transition_and_marks_should_end():
    repo = MagicMock()
    repo.get_act_context = AsyncMock(
        return_value={
            "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
            "sequences": [
                {"id": "seq-1", "name": "S1", "exit_triggers": []},
                {"id": "seq-2", "name": "S2", "exit_triggers": []},
                {"id": "seq-3", "name": "S3", "exit_triggers": []},
            ],
        }
    )
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "llm suggested backward",
            "next_act_id": None,
            "next_seq_id": "seq-2",
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-3",
        user_input="전투를 마무리한다",
        validator_agent=validator,
    )

    assert result.get("next_seq_id") is None
    assert result.get("should_end") is True
    assert "blocked non-forward" in result.get("reason", "")


@pytest.mark.asyncio
async def test_validate_progression_infers_next_act_and_seq_on_act_boundary_trigger():
    repo = MagicMock()

    async def _get_act_context(scenario_id: str, act_id: str):
        if act_id == "act-1":
            return {
                "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
                "sequences": [
                    {"id": "seq-1", "name": "S1", "exit_triggers": []},
                    {"id": "seq-2", "name": "S2", "exit_triggers": []},
                ],
            }
        if act_id == "act-2":
            return {
                "act": {"name": "A2", "goal": "G2", "exit_criteria": "E2"},
                "sequences": [{"id": "seq-3", "name": "S3", "exit_triggers": []}],
            }
        return None

    repo.get_act_context = AsyncMock(side_effect=_get_act_context)
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "triggered but no ids",
            "next_act_id": None,
            "next_seq_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-2",
        user_input="다음 단계로 이동한다",
        validator_agent=validator,
    )

    assert result["next_act_id"] == "act-2"
    assert result["next_seq_id"] == "seq-3"
    assert "inferred next_act_id/next_seq_id" in result["reason"]
    assert result.get("should_end") is not True


@pytest.mark.asyncio
async def test_validate_progression_infers_next_act_when_exit_trigger_matches():
    repo = MagicMock()

    async def _get_act_context(scenario_id: str, act_id: str):
        if act_id == "act-1":
            return {
                "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
                "sequences": [
                    {"id": "seq-1", "name": "S1", "exit_triggers": []},
                    {
                        "id": "seq-2",
                        "name": "S2",
                        "exit_triggers": ["다음 구역으로 이동한다."],
                    },
                ],
            }
        if act_id == "act-2":
            return {
                "act": {"name": "A2", "goal": "G2", "exit_criteria": "E2"},
                "sequences": [{"id": "seq-3", "name": "S3", "exit_triggers": []}],
            }
        return None

    repo.get_act_context = AsyncMock(side_effect=_get_act_context)
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": False,
            "reason": "llm undecided",
            "next_act_id": None,
            "next_seq_id": None,
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-2",
        user_input="정비를 마치고 다음 구역으로 이동한다.",
        validator_agent=validator,
    )

    assert result["next_act_id"] == "act-2"
    assert result["next_seq_id"] == "seq-3"
    assert result.get("is_triggered") is True


@pytest.mark.asyncio
async def test_validate_progression_recovers_when_non_forward_next_seq_is_blocked():
    repo = MagicMock()

    async def _get_act_context(scenario_id: str, act_id: str):
        if act_id == "act-1":
            return {
                "act": {"name": "A1", "goal": "G1", "exit_criteria": "E1"},
                "sequences": [
                    {"id": "seq-1", "name": "S1", "exit_triggers": []},
                    {
                        "id": "seq-2",
                        "name": "S2",
                        "exit_triggers": ["다음 구역으로 이동한다."],
                    },
                ],
            }
        if act_id == "act-2":
            return {
                "act": {"name": "A2", "goal": "G2", "exit_criteria": "E2"},
                "sequences": [{"id": "seq-3", "name": "S3", "exit_triggers": []}],
            }
        return None

    repo.get_act_context = AsyncMock(side_effect=_get_act_context)
    writer = MagicMock()
    validator = MagicMock()
    validator.run = AsyncMock(
        return_value={
            "is_triggered": True,
            "reason": "llm returned same sequence",
            "next_act_id": None,
            "next_seq_id": "seq-2",
            "suggested_narration": None,
        }
    )

    engine = ScenarioEngine(repository=repo, writer=writer)
    result = await engine.validate_progression(
        scenario_id="scn-1",
        act_id="act-1",
        seq_id="seq-2",
        user_input="다음 구역으로 이동한다.",
        validator_agent=validator,
    )

    assert result["next_act_id"] == "act-2"
    assert result["next_seq_id"] == "seq-3"
    assert "recovered act-boundary transition" in result["reason"]
