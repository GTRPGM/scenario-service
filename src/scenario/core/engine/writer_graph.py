import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from scenario.interfaces.agent import ScenarioAgent
from scenario.interfaces.rule_engine import RuleEngineRepository


class AgentState(TypedDict):
    concept: str
    assets: Dict[str, Any]
    plan: Dict[str, Any]
    content: Dict[str, Any]
    reviews: List[str]
    is_consistent: bool
    iterations: Annotated[int, operator.add]


class ScenarioWriterGraph:
    def __init__(
        self,
        planner: ScenarioAgent,
        writer: ScenarioAgent,
        reviewer: ScenarioAgent,
        rule_engine: Optional[RuleEngineRepository] = None,
    ):
        self.planner = planner
        self.writer = writer
        self.reviewer = reviewer
        self.rule_engine = rule_engine
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        graph = StateGraph(AgentState)

        graph.add_node("planner", self._planner_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("grounder", self._grounder_node)
        graph.add_node("reviewer", self._reviewer_node)

        graph.set_entry_point("planner")
        graph.add_edge("planner", "writer")
        graph.add_edge("writer", "grounder")
        graph.add_edge("grounder", "reviewer")

        graph.add_conditional_edges(
            "reviewer",
            self._should_continue,
            {"continue": "planner", "end": END},
        )
        return graph.compile()

    async def _planner_node(self, state: AgentState) -> Dict:
        input_data = {
            "concept": state["concept"],
            "assets": state.get("assets", {}),
            "previous_reviews": state.get("reviews", []),
            "iteration": state.get("iterations", 0) + 1,
        }
        result = await self.planner.run(input_data)
        return {"plan": result, "iterations": 1}

    async def _writer_node(self, state: AgentState) -> Dict:
        result = await self.writer.run(
            {
                "plan": state["plan"],
                "assets": state.get("assets", {}),
            }
        )
        return {"content": result}

    async def _grounder_node(self, state: AgentState) -> Dict:
        if not self.rule_engine or state.get("assets"):
            return {"content": state["content"]}

        content = state["content"]
        return {"content": content}

    async def _reviewer_node(self, state: AgentState) -> Dict:
        result = await self.reviewer.run(
            {
                "plan": state["plan"],
                "content": state["content"],
                "previous_reviews": state.get("reviews", []),
            }
        )
        return {
            "is_consistent": result.get("is_consistent", False),
            "reviews": result.get("reviews", []),
        }

    def _should_continue(self, state: AgentState) -> str:
        if state["is_consistent"]:
            return "end"
        if state["iterations"] >= 3:
            return "end"
        return "continue"

    async def run(self, concept: str, assets: Optional[Dict] = None) -> Dict:
        initial_state = {
            "concept": concept,
            "assets": assets or {},
            "plan": {},
            "content": {},
            "reviews": [],
            "is_consistent": False,
            "iterations": 0,
        }
        return await self.workflow.ainvoke(initial_state)
