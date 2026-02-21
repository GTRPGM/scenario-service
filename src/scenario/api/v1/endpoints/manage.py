import logging
from typing import Annotated, Any, Dict, List
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine

router = APIRouter()
logger = logging.getLogger(__name__)


class TransitionRequest(BaseModel):
    session_id: str
    next_act_id: str | None = None
    next_seq_id: str


class DebugInjectSaveRequest(BaseModel):
    payload: Dict[str, Any] | None = None
    planner_output: Dict[str, Any] | None = None
    writer_output: Dict[str, Any] | None = None
    relation_output: Dict[str, Any] | None = None
    concept: str = "debug-direct-inject"
    inject_to_state: bool = True


@router.get("/scenarios", response_model=List[Dict])
async def list_scenarios(
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """List all available scenarios."""
    return await engine.list_scenarios()


@router.post("/scenarios/{scenario_id}/inject", status_code=status.HTTP_200_OK)
async def inject_scenario(
    scenario_id: UUID,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Inject a scenario into the State Manager."""
    logger.info(f"Received injection request for scenario: {scenario_id}")
    try:
        return await engine.inject_to_state_manager(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        detail = f"Injection failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e


@router.post("/sessions/transition", status_code=status.HTTP_200_OK)
async def transition_session(
    request: TransitionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Transition a session to a new Act/Sequence."""
    try:
        return await engine.transition_session(
            session_id=request.session_id,
            next_act_id=request.next_act_id,
            next_seq_id=request.next_seq_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPStatusError as e:
        detail = f"State transition failed: {e.response.status_code}"
        raise HTTPException(status_code=502, detail=detail) from e
    except Exception as e:
        detail = f"Transition failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e


@router.post("/scenarios/debug/inject-save", status_code=status.HTTP_200_OK)
async def debug_inject_and_save_scenario(
    request: DebugInjectSaveRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Debug-only: save scenario payload into scenario-service and optionally inject to state-manager."""
    try:
        payload = request.payload
        if payload is None:
            stage_payload = {
                "planner_output": request.planner_output,
                "writer_output": request.writer_output,
                "relation_output": request.relation_output,
            }
            if any(v is not None for v in stage_payload.values()):
                payload = stage_payload
            else:
                raise ValueError(
                    "payload is required (or provide planner_output/writer_output/relation_output)"
                )
        return await engine.save_and_inject_debug(
            payload,
            concept=request.concept,
            inject_to_state=request.inject_to_state,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except httpx.HTTPStatusError as e:
        detail = f"State-manager inject failed: {e.response.status_code}"
        raise HTTPException(status_code=502, detail=detail) from e
    except Exception as e:
        detail = f"Debug inject/save failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e
