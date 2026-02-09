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
        current_plan = state.get("plan") or {}
        current_content = state.get("content") or {}

        def _plan_outline(plan: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(plan, dict):
                return {}
            acts = plan.get("acts") or []
            outline_acts = []
            for a in acts if isinstance(acts, list) else []:
                if not isinstance(a, dict):
                    continue
                outline_acts.append(
                    {
                        "id": a.get("id"),
                        "name": a.get("name"),
                        "sequences": a.get("sequences") or [],
                        "goal": a.get("goal"),
                        "exit_criteria": a.get("exit_criteria"),
                    }
                )
            return {
                "title": plan.get("title"),
                "difficulty": plan.get("difficulty"),
                "genre": plan.get("genre"),
                "total_acts": plan.get("total_acts"),
                "acts": outline_acts,
                "npc_ids": [
                    n.get("id")
                    for n in (plan.get("npc_manifest") or [])
                    if isinstance(n, dict)
                ],
                "enemy_ids": [
                    e.get("id")
                    for e in (plan.get("enemy_manifest") or [])
                    if isinstance(e, dict)
                ],
                "item_ids": [
                    i.get("id")
                    for i in (plan.get("item_manifest") or [])
                    if isinstance(i, dict)
                ],
            }

        def _content_outline(content: Dict[str, Any]) -> Dict[str, Any]:
            if not isinstance(content, dict):
                return {}
            seqs = content.get("sequences") or []
            out = []
            for s in seqs if isinstance(seqs, list) else []:
                if not isinstance(s, dict):
                    continue
                out.append(
                    {
                        "id": s.get("id"),
                        "sequence_type": s.get("sequence_type"),
                        "npcs": len(s.get("npcs") or [])
                        if isinstance(s.get("npcs"), list)
                        else None,
                        "enemies": len(s.get("enemies") or [])
                        if isinstance(s.get("enemies"), list)
                        else None,
                        "items": len(s.get("items") or [])
                        if isinstance(s.get("items"), list)
                        else None,
                        "exit_triggers": len(s.get("exit_triggers") or [])
                        if isinstance(s.get("exit_triggers"), list)
                        else None,
                    }
                )
            return {"sequences": out}

        input_data = {
            "concept": state["concept"],
            "assets": state.get("assets", {}),
            "current_plan_outline": _plan_outline(current_plan),
            "current_content_outline": _content_outline(current_content),
            "previous_reviews": state.get("reviews", []),
            "iteration": state.get("iterations", 0) + 1,
        }
        result = await self.planner.run(input_data)

        # Minimal deterministic fixes: avoid blank exit_criteria.
        try:
            if isinstance(result, dict):
                for act in result.get("acts") or []:
                    if not isinstance(act, dict):
                        continue
                    if not str(act.get("exit_criteria") or "").strip():
                        goal = str(act.get("goal") or "").strip()
                        act["exit_criteria"] = (
                            f"{goal}을(를) 달성하고 다음 구역으로 이동한다."
                            if goal
                            else "현재 액트의 목표를 달성하고 다음 구역으로 이동한다."
                        )
        except Exception:
            pass

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
                "previous_content": state.get("content", {}),
                "previous_reviews": state.get("reviews", []),
                "items": state.get("items", []),
                "npcs": state.get("npcs", []),
                "enemies": state.get("enemies", []),
                "assets": state.get("assets", {}),
            }
        )
        # Enforce minimal entity placement to keep state-manager scenarios usable.
        # The writer sometimes omits npcs/enemies on late sequences even when manifests exist.
        try:
            plan = state.get("plan") or {}
            npc_ids = [
                str(n.get("id")).strip()
                for n in (plan.get("npc_manifest") or [])
                if isinstance(n, dict) and str(n.get("id") or "").strip()
            ]
            enemy_ids = [
                str(e.get("id")).strip()
                for e in (plan.get("enemy_manifest") or [])
                if isinstance(e, dict) and str(e.get("id") or "").strip()
            ]
            item_ids = [
                str(i.get("id")).strip()
                for i in (plan.get("item_manifest") or [])
                if isinstance(i, dict) and str(i.get("id") or "").strip()
            ]
            sequences = result.get("sequences") if isinstance(result, dict) else None
            if isinstance(sequences, list) and (npc_ids or enemy_ids or item_ids):
                default_npc = npc_ids[0] if npc_ids else None
                default_enemy = enemy_ids[0] if enemy_ids else None
                default_item = item_ids[0] if item_ids else None

                for seq in sequences:
                    if not isinstance(seq, dict):
                        continue

                    npcs = seq.get("npcs")
                    enemies = seq.get("enemies")
                    items = seq.get("items")
                    if not isinstance(npcs, list):
                        npcs = []
                    if not isinstance(enemies, list):
                        enemies = []
                    if not isinstance(items, list):
                        items = []

                    npcs = [str(x).strip() for x in npcs if str(x).strip()]
                    enemies = [str(x).strip() for x in enemies if str(x).strip()]
                    items = [str(x).strip() for x in items if str(x).strip()]

                    seq_type = str(seq.get("sequence_type") or "").strip().lower()

                    # Always ensure at least 1 NPC if available.
                    if default_npc and not npcs:
                        npcs = [default_npc]

                    # Combat must include at least 1 enemy if available.
                    if default_enemy and "combat" in seq_type and not enemies:
                        enemies = [default_enemy]

                    # Ensure total entities >= 2 when possible.
                    total = len(npcs) + len(enemies)
                    if total < 2:
                        if default_enemy and default_enemy not in enemies:
                            enemies.append(default_enemy)
                        elif default_npc and default_npc not in npcs:
                            npcs.append(default_npc)

                    # Exploration/Puzzle should include at least 1 item if available.
                    if default_item and not items and (
                        "exploration" in seq_type or "puzzle" in seq_type
                    ):
                        items = [default_item]

                    seq["npcs"] = npcs
                    seq["enemies"] = enemies
                    seq["items"] = items
        except Exception:
            # Best-effort normalization; keep raw result if anything goes wrong.
            pass

        print("📍 [Graph] Sequence Writer complete.")
        return {"content": result}

    async def _grounder_node(self, state: AgentState) -> Dict:
        return {"content": state["content"]}

    async def _reviewer_node(self, state: AgentState) -> Dict:
        print("📍 [Graph] Running Reviewer...")
        # Deterministic validation: LLM reviewer tends to hallucinate failures even when
        # data is correct. We validate using the actual plan/content that will be
        # packaged for state-manager injection.
        plan = state.get("plan") or {}
        content = state.get("content") or {}

        reviews: list[str] = []

        acts = plan.get("acts") if isinstance(plan, dict) else []
        if not isinstance(acts, list) or not acts:
            reviews.append("acts가 비어 있습니다.")
        else:
            for act in acts:
                if not isinstance(act, dict):
                    continue
                if not str(act.get("description") or "").strip():
                    reviews.append(f"{act.get('id')} description 누락")
                if not str(act.get("goal") or "").strip():
                    reviews.append(f"{act.get('id')} goal 누락")
                if not str(act.get("exit_criteria") or "").strip():
                    reviews.append(f"{act.get('id')} exit_criteria 누락")
                seqs = act.get("sequences")
                if not isinstance(seqs, list) or not seqs:
                    reviews.append(f"{act.get('id')} sequences 누락")

        npc_ids = [
            str(n.get("id"))
            for n in (plan.get("npc_manifest") or [])
            if isinstance(n, dict) and n.get("id")
        ]
        enemy_ids = [
            str(e.get("id"))
            for e in (plan.get("enemy_manifest") or [])
            if isinstance(e, dict) and e.get("id")
        ]
        item_ids = [
            str(i.get("id"))
            for i in (plan.get("item_manifest") or [])
            if isinstance(i, dict) and i.get("id")
        ]
        if len(npc_ids) < 4:
            reviews.append("NPC가 최소 4명 필요합니다.")
        if len(enemy_ids) < 4:
            reviews.append("Enemy가 최소 4종 필요합니다.")
        if len(item_ids) < 4:
            reviews.append("Item/Object가 최소 4종 필요합니다.")

        seqs = content.get("sequences") if isinstance(content, dict) else []
        if not isinstance(seqs, list) or not seqs:
            reviews.append("content.sequences가 비어 있습니다.")
        else:
            # Coverage check: plan acts -> sequence IDs must match content sequence IDs
            plan_seq_ids: set[str] = set()
            for act in acts if isinstance(acts, list) else []:
                if isinstance(act, dict):
                    for sid in act.get("sequences") or []:
                        if sid:
                            plan_seq_ids.add(str(sid))

            content_seq_ids: set[str] = set()
            for s in seqs:
                if isinstance(s, dict) and s.get("id"):
                    content_seq_ids.add(str(s.get("id")))

            missing_in_content = sorted(plan_seq_ids - content_seq_ids)
            extra_in_content = sorted(content_seq_ids - plan_seq_ids)
            if missing_in_content:
                reviews.append(
                    f"plan에 있는 시퀀스가 content에 누락: {missing_in_content}"
                )
            if extra_in_content:
                reviews.append(
                    f"content에 plan에 없는 시퀀스가 포함: {extra_in_content}"
                )

            for s in seqs:
                if not isinstance(s, dict):
                    continue
                sid = s.get("id")
                if not str(s.get("description") or "").strip():
                    reviews.append(f"{sid} description 누락")
                if not str(s.get("goal") or "").strip():
                    reviews.append(f"{sid} goal 누락")
                if not isinstance(s.get("exit_triggers"), list) or not s.get(
                    "exit_triggers"
                ):
                    reviews.append(f"{sid} exit_triggers 누락")

                snpcs = s.get("npcs") or []
                senemies = s.get("enemies") or []
                sitems = s.get("items") or []
                if not isinstance(snpcsp:=snpcs, list):
                    snpcsp = []
                if not isinstance(senemies, list):
                    senemies = []
                if not isinstance(sitems, list):
                    sitems = []

                # Entity richness: NPC+Enemy >= 2
                if (len(snpcsp) + len(senemies)) < 2:
                    reviews.append(
                        f"{sid} 엔티티 부족: NPC({len(snpcsp)})+Enemy({len(senemies)})"
                    )

                stype = str(s.get("sequence_type") or "").lower()
                if ("exploration" in stype or "puzzle" in stype) and len(sitems) < 1:
                    reviews.append(f"{sid} 탐험/퍼즐 시퀀스에 items 누락")

                # Reference integrity (subset checks)
                for nid in snpcsp:
                    if str(nid) not in npc_ids:
                        reviews.append(f"{sid} 알 수 없는 npc id 참조: {nid}")
                for eid in senemies:
                    if str(eid) not in enemy_ids:
                        reviews.append(f"{sid} 알 수 없는 enemy id 참조: {eid}")
                for iid in sitems:
                    if str(iid) not in item_ids:
                        reviews.append(f"{sid} 알 수 없는 item id 참조: {iid}")

        is_consistent = len(reviews) == 0
        print(f"📍 [Graph] Reviewer complete. (Consistent: {is_consistent})")
        return {"is_consistent": is_consistent, "reviews": reviews}

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
