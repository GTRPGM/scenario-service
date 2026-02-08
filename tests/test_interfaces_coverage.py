from uuid import uuid4

import pytest

from scenario.interfaces.rule_engine import RuleEngineRepository
from scenario.interfaces.scenario import ScenarioRepository


class _RuleRepoSuperCall(RuleEngineRepository):
    async def bulk_grounding(self, scenario_data):
        # exercise abstract base method body for coverage
        return await super().bulk_grounding(scenario_data)

    async def get_all_assets(self):
        # exercise abstract base method body for coverage
        return await super().get_all_assets()


class _ScenarioRepoSuperCall(ScenarioRepository):
    async def save_scenario(self, concept, data):
        return uuid4()

    async def list_scenarios(self):
        return await super().list_scenarios()

    async def get_act_context(self, scenario_id, act_id):
        return await super().get_act_context(scenario_id, act_id)

    async def update_external_id(
        self, scenario_id, external_id, provider="state_manager"
    ):
        return await super().update_external_id(scenario_id, external_id, provider)

    async def update_session_state(self, session_id, act_id, seq_id, data):
        return await super().update_session_state(session_id, act_id, seq_id, data)

    async def get_session_state(self, session_id):
        return await super().get_session_state(session_id)


@pytest.mark.asyncio
async def test_interface_base_method_bodies_are_executable():
    rule_repo = _RuleRepoSuperCall()
    scenario_repo = _ScenarioRepoSuperCall()

    assert await rule_repo.bulk_grounding({"a": 1}) is None
    assert await rule_repo.get_all_assets() is None

    assert await scenario_repo.list_scenarios() is None
    assert await scenario_repo.get_act_context(uuid4(), "act-1") is None
    assert await scenario_repo.update_external_id(uuid4(), "ext") is None
    assert (
        await scenario_repo.update_session_state(uuid4(), "act-1", "seq-1", {}) is None
    )
    assert await scenario_repo.get_session_state(uuid4()) is None
