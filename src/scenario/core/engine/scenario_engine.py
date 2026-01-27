# src/scenario/core/engine/scenario_engine.py

from uuid import UUID

from scenario.interfaces.scenario import ScenarioRepository


class ScenarioEngine:
    """Core business logic for managing scenario progression."""

    def __init__(self, repository: ScenarioRepository):
        self.repository = repository

    async def check_progression(self, session_id: UUID, user_input: str) -> dict:
        state = await self.repository.get_session_state(session_id)

        # Core logic: Determine progression requirements
        return {
            "status": "active",
            "context": {
                "act": state["current_act_id"],
                "sequence": state["current_sequence_id"],
            },
            "goals": state["conditions"],
            "instruction": "Evaluate if the goals are met based on the user input.",
        }

    async def execute_transition(self, session_id: UUID, act_id: str, seq_id: str):
        await self.repository.update_session_state(session_id, act_id, seq_id, {})
