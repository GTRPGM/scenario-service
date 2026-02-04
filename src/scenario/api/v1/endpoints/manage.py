import logging
from typing import Annotated, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine

router = APIRouter()
logger = logging.getLogger(__name__)


class TransitionRequest(BaseModel):
    session_id: str
    next_act_id: str
    next_seq_id: str


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
    # TODO: Implement actual transition logic in Engine
    return {"status": "success"}
