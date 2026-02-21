import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from scenario.core.deps import (
    get_planner_agent,
    get_relation_agent,
    get_scenario_engine,
    get_scenario_repository,
    get_writer_agent,
)
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.interfaces.agent import ScenarioAgent
from scenario.plugins.db.adapter import PostgresScenarioAdapter

router = APIRouter()
CHECKPOINT_DIR = Path("/tmp/scenario-step-checkpoints")
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)


class GenerateScenarioRequest(BaseModel):
    concept: str


@router.post("/pure", status_code=status.HTTP_201_CREATED)
async def generate_pure(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Generate a scenario from scratch based on a concept."""
    return await engine.generate_pure(request.concept)


@router.post("/grounded", status_code=status.HTTP_201_CREATED)
async def generate_grounded(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Generate a scenario grounded in world settings."""
    return await engine.generate_grounded(request.concept)


@router.post("/informed", status_code=status.HTTP_201_CREATED)
async def generate_informed(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Generate a scenario with detailed domain knowledge."""
    return await engine.generate_informed(request.concept)


class PlannerStepRequest(BaseModel):
    concept: str
    run_id: Optional[str] = None
    assets: Dict[str, Any] = Field(default_factory=dict)
    current_plan: Optional[Dict[str, Any]] = None
    previous_defects: list[Dict[str, Any]] = Field(default_factory=list)
    iteration: int = 1


class WriterStepRequest(BaseModel):
    plan: Dict[str, Any]
    run_id: Optional[str] = None
    previous_content: Dict[str, Any] = Field(default_factory=dict)
    previous_defects: list[Dict[str, Any]] = Field(default_factory=list)
    previous_reviews: list[str] = Field(default_factory=list)
    items: list[Dict[str, Any]] = Field(default_factory=list)
    npcs: list[Dict[str, Any]] = Field(default_factory=list)
    enemies: list[Dict[str, Any]] = Field(default_factory=list)
    assets: Dict[str, Any] = Field(default_factory=dict)


class RelationStepRequest(BaseModel):
    plan: Dict[str, Any]
    run_id: Optional[str] = None
    sequences: list[Dict[str, Any]] = Field(default_factory=list)
    defects: list[Dict[str, Any]] = Field(default_factory=list)


class ContinueFromCheckpointRequest(BaseModel):
    checkpoint_id: str
    next_stage: Literal["writer", "relation"]
    run_id: Optional[str] = None
    overrides: Dict[str, Any] = Field(default_factory=dict)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checkpoint_path(checkpoint_id: str) -> Path:
    return CHECKPOINT_DIR / f"{checkpoint_id}.json"


def _save_checkpoint(
    stage: str, payload: Dict[str, Any], status_text: str
) -> Dict[str, Any]:
    checkpoint_id = uuid.uuid4().hex[:12]
    record = {
        "checkpoint_id": checkpoint_id,
        "stage": stage,
        "status": status_text,
        "created_at": _utc_now(),
        **payload,
    }
    path = _checkpoint_path(checkpoint_id)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return {
        "checkpoint_id": checkpoint_id,
        "checkpoint_path": str(path),
        "record": record,
    }


def _load_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    path = _checkpoint_path(checkpoint_id)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_id}")
    return json.loads(path.read_text(encoding="utf-8"))


async def _ensure_run_id(
    repository: PostgresScenarioAdapter,
    run_id: Optional[str],
    concept: str,
) -> str:
    if run_id:
        try:
            uuid.UUID(str(run_id))
            return str(run_id)
        except ValueError:
            logger.warning("Invalid run_id=%s. Creating a new run.", run_id)
    return str(await repository.create_generation_run(concept))


async def _run_stage(
    *,
    stage: str,
    agent: ScenarioAgent,
    resolved_input: Dict[str, Any],
    repository: PostgresScenarioAdapter,
    run_id: str,
    endpoint: str,
    request_payload: Dict[str, Any],
    retry_count: int,
) -> Dict[str, Any]:
    attempt_count = retry_count + 1
    status_text = "success"
    result: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None

    try:
        result = await agent.run(resolved_input)
        status_text = "success"
        error_text = None
        saved = _save_checkpoint(
            stage=stage,
            payload={
                "run_id": run_id,
                "attempt_count": attempt_count,
                "resolved_input": resolved_input,
                "result": result,
                "error": error_text,
            },
            status_text=status_text,
        )
        response_payload = {
            "status": "success",
            "stage": stage,
            "run_id": run_id,
            "attempt_count": attempt_count,
            "retry_count": retry_count,
            "checkpoint_id": saved["checkpoint_id"],
            "checkpoint_path": saved["checkpoint_path"],
            "result": result,
        }
    except (
        Exception
    ) as exc:  # pragma: no cover - handled by tests through response shape
        status_text = "error"
        error_text = str(exc)
        saved = _save_checkpoint(
            stage=stage,
            payload={
                "run_id": run_id,
                "attempt_count": attempt_count,
                "resolved_input": resolved_input,
                "result": None,
                "error": error_text,
            },
            status_text=status_text,
        )
        response_payload = {
            "status": "error",
            "stage": stage,
            "run_id": run_id,
            "attempt_count": attempt_count,
            "retry_count": retry_count,
            "checkpoint_id": saved["checkpoint_id"],
            "checkpoint_path": saved["checkpoint_path"],
            "error": error_text,
        }

    db_logging_ok = True
    try:
        await repository.save_generation_step(
            run_id=run_id,
            checkpoint_id=saved["checkpoint_id"],
            stage=stage,
            status=status_text,
            attempt_count=attempt_count,
            resolved_input=resolved_input,
            result=result,
            error=error_text,
        )
        await repository.log_generation_request(
            run_id=run_id,
            stage=stage,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response_payload,
            status=status_text,
            retry_count=retry_count,
            error=error_text,
        )
    except Exception:
        db_logging_ok = False
        logger.exception(
            "Failed to persist generation logs for stage=%s run_id=%s", stage, run_id
        )

    response_payload["db_logging_ok"] = db_logging_ok
    return response_payload


@router.post("/step/planner", status_code=status.HTTP_200_OK)
async def generate_step_planner(
    request: PlannerStepRequest,
    planner: Annotated[ScenarioAgent, Depends(get_planner_agent)],
    repository: Annotated[PostgresScenarioAdapter, Depends(get_scenario_repository)],
):
    run_id = await _ensure_run_id(repository, request.run_id, request.concept)
    retry_count = await repository.count_generation_requests_for_stage(
        run_id, "planner"
    )
    resolved_input = {
        "concept": request.concept,
        "assets": request.assets,
        "current_plan": request.current_plan,
        "previous_defects": request.previous_defects,
        "iteration": request.iteration,
    }
    return await _run_stage(
        stage="planner",
        agent=planner,
        resolved_input=resolved_input,
        repository=repository,
        run_id=run_id,
        endpoint="/api/v1/generation/step/planner",
        request_payload=request.model_dump(),
        retry_count=retry_count,
    )


@router.post("/step/writer", status_code=status.HTTP_200_OK)
async def generate_step_writer(
    request: WriterStepRequest,
    writer: Annotated[ScenarioAgent, Depends(get_writer_agent)],
    repository: Annotated[PostgresScenarioAdapter, Depends(get_scenario_repository)],
):
    run_id = await _ensure_run_id(repository, request.run_id, "step-writer")
    retry_count = await repository.count_generation_requests_for_stage(run_id, "writer")
    resolved_input = request.model_dump()
    resolved_input.pop("run_id", None)
    return await _run_stage(
        stage="writer",
        agent=writer,
        resolved_input=resolved_input,
        repository=repository,
        run_id=run_id,
        endpoint="/api/v1/generation/step/writer",
        request_payload=request.model_dump(),
        retry_count=retry_count,
    )


@router.post("/step/relation", status_code=status.HTTP_200_OK)
async def generate_step_relation(
    request: RelationStepRequest,
    relation_manager: Annotated[ScenarioAgent, Depends(get_relation_agent)],
    repository: Annotated[PostgresScenarioAdapter, Depends(get_scenario_repository)],
):
    run_id = await _ensure_run_id(repository, request.run_id, "step-relation")
    retry_count = await repository.count_generation_requests_for_stage(
        run_id, "relation"
    )
    plan = request.plan
    resolved_input = {
        "plan": plan,
        "sequences": request.sequences,
        "draft_relations": plan.get("relations") or [],
        "npcs": plan.get("npc_manifest", []),
        "enemies": plan.get("enemy_manifest", []),
        "items": plan.get("item_manifest", []),
        "defects": [d for d in request.defects if d.get("field") == "relations"],
    }
    return await _run_stage(
        stage="relation",
        agent=relation_manager,
        resolved_input=resolved_input,
        repository=repository,
        run_id=run_id,
        endpoint="/api/v1/generation/step/relation",
        request_payload=request.model_dump(),
        retry_count=retry_count,
    )


@router.post("/step/continue", status_code=status.HTTP_200_OK)
async def continue_from_checkpoint(
    request: ContinueFromCheckpointRequest,
    writer: Annotated[ScenarioAgent, Depends(get_writer_agent)],
    relation_manager: Annotated[ScenarioAgent, Depends(get_relation_agent)],
    repository: Annotated[PostgresScenarioAdapter, Depends(get_scenario_repository)],
):
    checkpoint = _load_checkpoint(request.checkpoint_id)
    run_id = await _ensure_run_id(
        repository,
        request.run_id or checkpoint.get("run_id"),
        "step-continue",
    )
    base_result = checkpoint.get("result") or {}
    base_input = checkpoint.get("resolved_input") or {}
    overrides = request.overrides or {}

    if request.next_stage == "writer":
        # planner result -> writer input
        resolved_input = {
            "plan": overrides.get("plan")
            or base_result
            or base_input.get("plan")
            or {},
            "previous_content": overrides.get("previous_content", {}),
            "previous_defects": overrides.get("previous_defects", []),
            "previous_reviews": overrides.get("previous_reviews", []),
            "items": overrides.get("items", []),
            "npcs": overrides.get("npcs", []),
            "enemies": overrides.get("enemies", []),
            "assets": overrides.get("assets", {}),
        }
        retry_count = await repository.count_generation_requests_for_stage(
            run_id, "writer"
        )
        return await _run_stage(
            stage="writer",
            agent=writer,
            resolved_input=resolved_input,
            repository=repository,
            run_id=run_id,
            endpoint="/api/v1/generation/step/continue",
            request_payload=request.model_dump(),
            retry_count=retry_count,
        )

    # writer result -> relation input
    plan = overrides.get("plan") or base_input.get("plan") or {}
    content = overrides.get("content") or base_result or {}
    resolved_input = {
        "plan": plan,
        "sequences": content.get("sequences", []),
        "draft_relations": plan.get("relations") or [],
        "npcs": plan.get("npc_manifest", []),
        "enemies": plan.get("enemy_manifest", []),
        "items": plan.get("item_manifest", []),
        "defects": overrides.get("defects", []),
    }
    retry_count = await repository.count_generation_requests_for_stage(
        run_id, "relation"
    )
    return await _run_stage(
        stage="relation",
        agent=relation_manager,
        resolved_input=resolved_input,
        repository=repository,
        run_id=run_id,
        endpoint="/api/v1/generation/step/continue",
        request_payload=request.model_dump(),
        retry_count=retry_count,
    )


@router.get("/step/checkpoints/{checkpoint_id}", status_code=status.HTTP_200_OK)
async def get_step_checkpoint(checkpoint_id: str):
    checkpoint = _load_checkpoint(checkpoint_id)
    return {"status": "success", "data": checkpoint}


@router.get("/step/runs/{run_id}", status_code=status.HTTP_200_OK)
async def get_step_run_report(
    run_id: str,
    repository: Annotated[PostgresScenarioAdapter, Depends(get_scenario_repository)],
):
    try:
        uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid run_id format") from exc

    report = await repository.get_generation_run_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return {"status": "success", "data": report}
