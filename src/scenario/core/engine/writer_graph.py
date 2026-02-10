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
    defects: List[Dict[str, Any]]  # Structured defects
    is_consistent: bool
    iterations: Annotated[int, operator.add]

    # Stage results
    plan_consistent: bool
    asset_consistent: bool
    writer_consistent: bool
    failed_asset_ids: List[str]


class ScenarioWriterGraph:
    def __init__(
        self,
        planner: ScenarioAgent,
        writer: ScenarioAgent,
        reviewer: ScenarioAgent,
        asset_writer: Optional[ScenarioAgent] = None,
        relation_manager: Optional[ScenarioAgent] = None,
        plan_reviewer: Optional[ScenarioAgent] = None,
        asset_reviewer: Optional[ScenarioAgent] = None,
        writer_reviewer: Optional[ScenarioAgent] = None,
        rule_engine: Optional[RuleEngineRepository] = None,
    ):
        self.planner = planner
        self.asset_writer = asset_writer
        self.relation_manager = relation_manager
        self.writer = writer
        self.reviewer = reviewer
        self.plan_reviewer = plan_reviewer
        self.asset_reviewer = asset_reviewer
        self.writer_reviewer = writer_reviewer
        self.rule_engine = rule_engine
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        graph = StateGraph(AgentState)

        # Nodes
        graph.add_node("planner", self._planner_node)
        graph.add_node("plan_reviewer", self._plan_reviewer_node)

        graph.add_node("writer", self._writer_node)
        graph.add_node("writer_reviewer", self._writer_reviewer_node)

        if self.relation_manager:
            graph.add_node("relation_manager", self._relation_manager_node)

        if self.asset_writer:
            graph.add_node("asset_writer", self._asset_writer_node)
            graph.add_node("asset_reviewer", self._asset_reviewer_node)

        graph.add_node("grounder", self._grounder_node)
        graph.add_node("reviewer", self._reviewer_node)

        # Edges
        graph.set_entry_point("planner")

        # Stage 1: Planning
        graph.add_edge("planner", "plan_reviewer")
        graph.add_conditional_edges(
            "plan_reviewer",
            self._should_continue_plan,
            {"continue": "planner", "next": "writer", "end": END},
        )

        # Stage 2: Writing Sequences
        graph.add_edge("writer", "writer_reviewer")
        graph.add_conditional_edges(
            "writer_reviewer",
            self._should_continue_writer,
            {
                "continue": "writer",
                "next": "relation_manager"
                if self.relation_manager
                else ("asset_writer" if self.asset_writer else "grounder"),
                "end": END,
            },
        )

        # Stage 3: Relation Management
        if self.relation_manager:
            graph.add_edge(
                "relation_manager", "asset_writer" if self.asset_writer else "grounder"
            )

        # Stage 4: Assets
        if self.asset_writer:
            graph.add_edge("asset_writer", "asset_reviewer")
            graph.add_conditional_edges(
                "asset_reviewer",
                self._should_continue_asset,
                {"continue": "asset_writer", "next": "grounder", "end": END},
            )

        # Final Stage
        graph.add_edge("grounder", "reviewer")
        graph.add_conditional_edges(
            "reviewer",
            self._should_continue_global,
            {"continue": "planner", "end": END},
        )

        return graph.compile()

    async def _planner_node(self, state: AgentState) -> Dict:
        print(f"📍 [Planner] Running... (Total Iter: {state.get('iterations', 0)})")
        current_plan = state.get("plan") or {}
        defects = state.get("defects", [])

        # 필터링: 결함이 있는 필드나 엔티티만 수정 대상으로 LLM에 전달
        input_data = {
            "concept": state["concept"],
            "assets": state.get("assets", {}),
            "current_plan": current_plan if current_plan else None,
            "previous_defects": defects,
            "iteration": state.get("iterations", 0) + 1,
        }
        result = await self.planner.run(input_data)

        # 병합 로직: LLM이 보낸 부분 데이터를 기존 플랜에 병합
        new_plan = current_plan.copy() if current_plan else {}
        if isinstance(result, dict):
            for k, v in result.items():
                if isinstance(v, list) and k in [
                    "acts",
                    "npc_manifest",
                    "enemy_manifest",
                    "item_manifest",
                    "relations",
                ]:
                    # 리스트 타입(엔티티 등)은 ID 기반 병합
                    existing_items = {
                        str(item.get("id")): item for item in new_plan.get(k, [])
                    }
                    for item in v:
                        iid = str(item.get("id"))
                        if iid:
                            existing_items[iid] = item
                    new_plan[k] = list(existing_items.values())
                else:
                    # 단일 필드(title, description 등)는 덮어쓰기
                    new_plan[k] = v

        return {"plan": new_plan, "iterations": 1}

    async def _writer_node(self, state: AgentState) -> Dict:
        print(
            f"📍 [Sequence Writer] Running... (Total Iter: {state.get('iterations', 0)})"
        )
        current_content = state.get("content") or {}
        defects = [d for d in state.get("defects", []) if "seq-" in str(d.get("id"))]

        result = await self.writer.run(
            {
                "plan": state["plan"],
                "previous_content": current_content,
                "previous_defects": defects,
                "items": state.get("items", []),
                "npcs": state.get("npcs", []),
                "enemies": state.get("enemies", []),
                "assets": state.get("assets", {}),
            }
        )

        # 시퀀스 병합 로직
        new_sequences = {
            str(s.get("id")): s for s in current_content.get("sequences", [])
        }
        if isinstance(result.get("sequences"), list):
            for s in result["sequences"]:
                sid = str(s.get("id"))
                if sid:
                    new_sequences[sid] = s

        # 관계 제안 병합
        all_relations = (state["plan"].get("relations") or []) + (
            result.get("relations") or []
        )
        state["plan"]["relations"] = all_relations

        return {"content": {"sequences": list(new_sequences.values())}, "iterations": 1}

    async def _relation_manager_node(self, state: AgentState) -> Dict:
        print("📍 [Relation Manager] Consolidating Relations...")
        plan = state.get("plan") or {}
        content = state.get("content") or {}
        defects = [d for d in state.get("defects", []) if d.get("field") == "relations"]

        # 문맥 필터링: 결함이 있는 관계와 관련된 시퀀스/엔티티만 추출
        relevant_seq_ids = set()
        if defects:
            for d in defects:
                # 결함이 발생한 엔티티 ID가 포함된 시퀀스 찾기
                target_id = str(d.get("id"))
                for s in content.get("sequences", []):
                    if target_id in (
                        s.get("npcs", []) + s.get("enemies", []) + s.get("items", [])
                    ):
                        relevant_seq_ids.add(s["id"])

        filtered_sequences = [
            s
            for s in content.get("sequences", [])
            if not relevant_seq_ids or s["id"] in relevant_seq_ids
        ]

        input_data = {
            "plan": plan,
            "sequences": filtered_sequences,
            "draft_relations": plan.get("relations") or [],
            "npcs": plan.get("npc_manifest", []),
            "enemies": plan.get("enemy_manifest", []),
            "items": plan.get("item_manifest", []),
            "defects": defects,
        }

        result = await self.relation_manager.run(input_data)
        plan["relations"] = result.get("relations", [])
        return {"plan": plan}

    async def _asset_writer_node(self, state: AgentState) -> Dict:
        print(
            f"📍 [Asset Writer] Running... (Total Iter: {state.get('iterations', 0)})"
        )
        plan = state["plan"]
        content = state.get("content", {})
        defects = state.get("defects", [])
        failed_ids = set(state.get("failed_asset_ids", []))

        npc_m = plan.get("npc_manifest", [])
        enemy_m = plan.get("enemy_manifest", [])
        item_m = plan.get("item_manifest", [])

        # 문맥 필터링: 수정이 필요한 엔티티와 관련된 시퀀스 및 관계만 추출
        relevant_ids = (
            failed_ids
            if failed_ids
            else {str(m["id"]) for m in (npc_m + enemy_m + item_m)}
        )
        filtered_sequences = [
            s
            for s in content.get("sequences", [])
            if any(
                rid in (s.get("npcs", []) + s.get("enemies", []) + s.get("items", []))
                for rid in relevant_ids
            )
        ]
        filtered_relations = [
            r
            for r in plan.get("relations", [])
            if str(r.get("from_id")) in relevant_ids
            or str(r.get("to_id")) in relevant_ids
        ]

        if failed_ids:
            npc_m = [m for m in npc_m if str(m.get("id")) in failed_ids]
            enemy_m = [m for m in enemy_m if str(m.get("id")) in failed_ids]
            item_m = [m for m in item_m if str(m.get("id")) in failed_ids]

        result = await self.asset_writer.run(
            {
                "context_plan": plan,
                "associated_sequences": filtered_sequences,
                "associated_relations": filtered_relations,
                "item_manifest": item_m,
                "npc_manifest": npc_m,
                "enemy_manifest": enemy_m,
                "current_catalog": {
                    "items": state.get("items", []),
                    "npcs": state.get("npcs", []),
                    "enemies": state.get("enemies", []),
                },
                "previous_defects": defects,
            }
        )

        def merge(existing: List[Dict], new: List[Dict], key: str) -> List[Dict]:
            merged_map = {str(e.get(key)): e for e in existing if e.get(key)}
            for n in new:
                nid = str(n.get(key))
                if nid:
                    merged_map[nid] = n
            return list(merged_map.values())

        return {
            "items": merge(state.get("items", []), result.get("items", []), "item_id"),
            "npcs": merge(
                state.get("npcs", []), result.get("npcs", []), "scenario_npc_id"
            ),
            "enemies": merge(
                state.get("enemies", []), result.get("enemies", []), "scenario_enemy_id"
            ),
            "iterations": 1,
        }

    async def _asset_reviewer_node(self, state: AgentState) -> Dict:
        print("🔎 [Reviewer] Inspecting Assets...")
        if not self.asset_reviewer:
            return {"asset_consistent": True, "failed_asset_ids": []}
        result = await self.asset_reviewer.run(
            {
                "plan": state["plan"],
                "items": state["items"],
                "npcs": state["npcs"],
                "enemies": state["enemies"],
            }
        )
        is_consistent = bool(result.get("is_consistent"))
        reviews = result.get("reviews", [])
        defects = result.get("defects", [])
        failed_ids = (
            [d.get("id") for d in defects if d.get("id")] if not is_consistent else []
        )
        if not is_consistent:
            print(f"❌ [Reviewer] Assets Rejected. Defects: {defects}")
        else:
            print("✅ [Reviewer] Assets Passed.")
        return {
            "asset_consistent": is_consistent,
            "reviews": reviews,
            "defects": defects,
            "failed_asset_ids": failed_ids,
        }

    async def _writer_node(self, state: AgentState) -> Dict:
        print(
            f"📍 [Sequence Writer] Running... (Total Iter: {state.get('iterations', 0)})"
        )
        result = await self.writer.run(
            {
                "plan": state["plan"],
                "previous_content": state.get("content", {}),
                "previous_reviews": state.get("reviews", []),
                "previous_defects": state.get("defects", []),
                "items": state.get("items", []),
                "npcs": state.get("npcs", []),
                "enemies": state.get("enemies", []),
                "assets": state.get("assets", {}),
            }
        )
        try:
            plan = state.get("plan") or {}
            npc_ids = [str(n.get("id")) for n in plan.get("npc_manifest", [])]
            enemy_ids = [str(e.get("id")) for e in plan.get("enemy_manifest", [])]
            item_ids = [str(i.get("id")) for i in plan.get("item_manifest", [])]
            if isinstance(result.get("sequences"), list):
                d_npc, d_enemy, d_item = (
                    (npc_ids[0] if npc_ids else None),
                    (enemy_ids[0] if enemy_ids else None),
                    (item_ids[0] if item_ids else None),
                )
                for s in result["sequences"]:
                    n, e, i = (
                        [str(x) for x in (s.get("npcs") or [])],
                        [str(x) for x in (s.get("enemies") or [])],
                        [str(x) for x in (s.get("items") or [])],
                    )
                    if (len(n) + len(e) + len(i)) < 2:
                        if d_npc and d_npc not in n:
                            n.append(d_npc)
                        if (
                            (len(n) + len(e) + len(i)) < 2
                            and d_enemy
                            and d_enemy not in e
                        ):
                            e.append(d_enemy)
                    s["npcs"], s["enemies"], s["items"] = n, e, i
        except:
            pass
        return {"content": result, "iterations": 1}

    async def _writer_reviewer_node(self, state: AgentState) -> Dict:
        print("🔎 [Reviewer] Inspecting Sequences...")
        if not self.writer_reviewer:
            return {"writer_consistent": True}
        result = await self.writer_reviewer.run(
            {"plan": state["plan"], "content": state["content"]}
        )
        is_consistent = bool(result.get("is_consistent"))
        reviews = result.get("reviews", [])
        defects = result.get("defects", [])
        if not is_consistent:
            print(f"❌ [Reviewer] Sequences Rejected. Defects: {defects}")
        else:
            print("✅ [Reviewer] Sequences Passed.")
        return {
            "writer_consistent": is_consistent,
            "reviews": reviews,
            "defects": defects,
        }

    async def _grounder_node(self, state: AgentState) -> Dict:
        return {"content": state["content"]}

    async def _reviewer_node(self, state: AgentState) -> Dict:
        print("🔎 [Reviewer] Inspecting Global Consistency...")
        result = await self.reviewer.run(
            {"plan": state.get("plan", {}), "content": state.get("content", {})}
        )
        is_consistent = bool(result.get("is_consistent"))
        reviews = result.get("reviews", [])
        defects = result.get("defects", [])
        if not is_consistent:
            print(f"❌ [Reviewer] Global Consistency Rejected. Defects: {defects}")
        else:
            print("✅ [Reviewer] Global Consistency Passed.")
        return {
            "is_consistent": is_consistent,
            "reviews": reviews,
            "defects": defects,
            "iterations": 1,
        }

    # Conditional Edges
    def _should_continue_plan(self, state: AgentState) -> str:
        if state["plan_consistent"]:
            return "next"
        if state["iterations"] >= 15:
            return "end"
        return "continue"

    def _should_continue_asset(self, state: AgentState) -> str:
        if state["asset_consistent"]:
            return "next"
        if state["iterations"] >= 15:
            return "end"
        return "continue"

    def _should_continue_writer(self, state: AgentState) -> str:
        if state["writer_consistent"]:
            return "next"
        if state["iterations"] >= 15:
            return "end"
        return "continue"

    def _should_continue_global(self, state: AgentState) -> str:
        if state["is_consistent"] or state["iterations"] >= 15:
            return "end"
        return "continue"

    async def run(self, concept: str, assets: Optional[Dict] = None) -> Dict:
        return await self.workflow.ainvoke(
            {
                "concept": concept,
                "assets": assets or {},
                "plan": {},
                "items": [],
                "npcs": [],
                "enemies": [],
                "content": {},
                "reviews": [],
                "defects": [],
                "is_consistent": False,
                "iterations": 0,
                "plan_consistent": False,
                "asset_consistent": False,
                "writer_consistent": False,
                "failed_asset_ids": [],
            }
        )
