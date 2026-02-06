import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from scenario.interfaces.agent import ScenarioAgent
from scenario.interfaces.rule_engine import RuleEngineRepository


class AgentState(TypedDict):
    concept: str
    assets: Dict[str, Any]  # World settings/master data
    plan: Dict[str, Any]  # High-level plan + Manifests

    # Global Asset Catalog
    items: List[Dict[str, Any]]
    npcs: List[Dict[str, Any]]
    enemies: List[Dict[str, Any]]

    content: Dict[str, Any]  # Sequence details (references IDs)
    reviews: List[str]
    is_consistent: bool
    iterations: Annotated[int, operator.add]


class ScenarioWriterGraph:
    def __init__(
        self,
        planner: ScenarioAgent,
        writer: ScenarioAgent,
        reviewer: ScenarioAgent,
        asset_writer: Optional[ScenarioAgent] = None,
        rule_engine: Optional[RuleEngineRepository] = None,
    ):
        self.planner = planner
        self.asset_writer = asset_writer
        self.writer = writer
        self.reviewer = reviewer
        self.rule_engine = rule_engine
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        graph = StateGraph(AgentState)

        graph.add_node("planner", self._planner_node)
        if self.asset_writer:
            graph.add_node("asset_writer", self._asset_writer_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("grounder", self._grounder_node)
        graph.add_node("reviewer", self._reviewer_node)

        graph.set_entry_point("planner")

        if self.asset_writer:
            graph.add_edge("planner", "asset_writer")
            graph.add_edge("asset_writer", "writer")
        else:
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
        print("📍 [Graph] Running Planner...")
        input_data = {
            "concept": state["concept"],
            "assets": state.get("assets", {}),
            "previous_reviews": state.get("reviews", []),
            "iteration": state.get("iterations", 0) + 1,
        }
        result = await self.planner.run(input_data)
        print("📍 [Graph] Planner complete.")
        return {"plan": result, "iterations": 1}

    async def _asset_writer_node(self, state: AgentState) -> Dict:
        if not self.asset_writer:
            return {"items": [], "npcs": [], "enemies": []}

        print("📍 [Graph] Running Asset Writer...")
        plan = state["plan"]
        result = await self.asset_writer.run(
            {
                "item_manifest": plan.get("item_manifest", []),
                "npc_manifest": plan.get("npc_manifest", []),
                "enemy_manifest": plan.get("enemy_manifest", []),
            }
        )
        print("📍 [Graph] Asset Writer complete.")
        return {
            "items": result.get("items", []),
            "npcs": result.get("npcs", []),
            "enemies": result.get("enemies", []),
        }

    async def _writer_node(self, state: AgentState) -> Dict:
        print("📍 [Graph] Running Sequence Writer...")
        # Pass the entire catalog to the sequence writer
        result = await self.writer.run(
            {
                "plan": state["plan"],
                "items": state.get("items", []),
                "npcs": state.get("npcs", []),
                "enemies": state.get("enemies", []),
                "assets": state.get("assets", {}),
            }
        )
        print("📍 [Graph] Sequence Writer complete.")
        return {"content": result}

    async def _grounder_node(self, state: AgentState) -> Dict:
        return {"content": state["content"]}

    async def _reviewer_node(self, state: AgentState) -> Dict:
        print("📍 [Graph] Running Reviewer...")
        result = await self.reviewer.run(
            {
                "plan": state["plan"],
                "items": state.get("items", []),
                "npcs": state.get("npcs", []),
                "enemies": state.get("enemies", []),
                "content": state["content"],
                "previous_reviews": state.get("reviews", []),
            }
        )
        is_consistent = result.get("is_consistent", False)
        print(f"📍 [Graph] Reviewer complete. (Consistent: {is_consistent})")
        return {
            "is_consistent": is_consistent,
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
            "items": [],
            "npcs": [],
            "enemies": [],
            "content": {},
            "reviews": [],
            "is_consistent": False,
            "iterations": 0,
        }
        return await self.workflow.ainvoke(initial_state)
