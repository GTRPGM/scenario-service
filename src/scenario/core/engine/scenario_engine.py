# src/scenario/core/engine/scenario_engine.py

import uuid
from typing import Dict, List

from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.interfaces.scenario import ScenarioRepository


class ScenarioEngine:
    """Core engine for scenario management and generation."""

    def __init__(self, repository: ScenarioRepository, writer: ScenarioWriterGraph):
        self.repository = repository
        self.writer = writer

    async def generate_scenario(self, concept: str) -> Dict:
        """Triggers the multi-agent generation workflow and persists the result."""
        final_state = await self.writer.run(concept)
        scenario_id = uuid.uuid4()
        scenario_data = {
            "summary": final_state["plan"].get("total_summary"),
            "acts": final_state["plan"].get("acts"),
            "sequences": final_state["content"].get("sequences"),
        }
        await self.repository.save_scenario(scenario_id, concept, scenario_data)
        return {
            "status": "success",
            "scenario_id": str(scenario_id),
            "summary": scenario_data["summary"],
            "data": scenario_data,
        }

    async def list_scenarios(self) -> List[Dict]:
        return await self.repository.list_scenarios()

    async def initialize_session(
        self, session_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> Dict:
        """Create a new session instance from a scenario template."""
        # 1. Fetch scenario graph
        graph = await self.repository.get_scenario_full_graph(scenario_id)
        if not graph:
            raise ValueError(f"Scenario {scenario_id} not found")

        # 2. Determine initial entry point
        # Convention: The first Act and its first Sequence
        first_act = graph["acts"][0]
        first_seq = first_act["sequences"][0]

        # 3. Persist session state
        await self.repository.create_session(
            session_id, scenario_id, first_act["id"], first_seq["id"]
        )

        # 4. Construct complete response
        return {
            "session_id": str(session_id),
            "scenario": {
                "id": str(scenario_id),
                "concept": graph["concept"],
                "summary": graph["summary"],
            },
            "current_state": {
                "act": {"id": first_act["id"], "name": first_act["name"]},
                "sequence": first_seq,
            },
        }

    async def check_progression(self, session_id: uuid.UUID, user_input: str) -> dict:
        state = await self.repository.get_session_state(session_id)
        if not state:
            return {"status": "error", "message": "Session not found"}

        return {
            "status": "active",
            "context": {
                "act": state["current_act_id"],
                "sequence": state["current_sequence_id"],
            },
            "goals": ["목표 달성 여부 확인 필요"],  # TODO: Load actual goals from graph
            "instruction": "Evaluate progress based on user input.",
        }

    async def execute_transition(self, session_id: uuid.UUID, act_id: str, seq_id: str):
        await self.repository.update_session_state(session_id, act_id, seq_id, {})
