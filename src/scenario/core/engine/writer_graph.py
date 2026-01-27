# src/scenario/core/engine/writer_graph.py

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from scenario.interfaces.agent import ScenarioAgent


class AgentState(TypedDict):
    concept: str
    plan: Dict[str, Any]
    content: Dict[str, Any]  # Changed from List to Dict to match WriterOutput
    reviews: List[str]
    is_consistent: bool
    iterations: int


class ScenarioWriterGraph:
    """
    Multi-agent workflow using injected agent implementations
    with structured outputs.
    """

    def __init__(
        self, planner: ScenarioAgent, writer: ScenarioAgent, reviewer: ScenarioAgent
    ):
        self.planner = planner
        self.writer = writer
        self.reviewer = reviewer
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        graph = StateGraph(AgentState)

        graph.add_node("planner", self._planner_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("reviewer", self._reviewer_node)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "writer")
        graph.add_edge("writer", "reviewer")

        graph.add_conditional_edges(
            "reviewer",
            self._should_continue,
            {"continue": "planner", "end": END},
        )
        return graph.compile()

    async def _planner_node(self, state: AgentState) -> Dict:
        # Planner outputs {'acts': [...], 'total_summary': '...'}
        result = await self.planner.run({"concept": state["concept"]})
        return {"plan": result, "iterations": state.get("iterations", 0) + 1}

    async def _writer_node(self, state: AgentState) -> Dict:
        # Writer outputs {'sequences': [...]}
        result = await self.writer.run({"plan": state["plan"]})
        return {"content": result}

    async def _reviewer_node(self, state: AgentState) -> Dict:
        # Reviewer outputs {'is_consistent': bool, 'reviews': [...]}
        result = await self.reviewer.run(
            {
                "plan": state["plan"],
                "content": state["content"],
            }
        )
        return result

    def _should_continue(self, state: AgentState) -> str:
        # Loop back if not consistent, but limit iterations to avoid infinite costs
        if state["is_consistent"] or state["iterations"] >= 3:
            return "end"
        return "continue"

    async def run(self, concept: str) -> Dict:
        initial_state = {
            "concept": concept,
            "plan": {},
            "content": {},
            "reviews": [],
            "is_consistent": False,
            "iterations": 0,
        }
        return await self.workflow.ainvoke(initial_state)
