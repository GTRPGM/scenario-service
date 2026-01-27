# src/scenario/api/v1/endpoints/scenario.py

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine

router = APIRouter()


class ProgressionCheckRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_id: UUID
    user_input: str


class TransitionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_id: UUID
    next_act_id: str
    next_seq_id: str


@router.post("/check")
async def check_progression(
    request: ProgressionCheckRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Check if the player's action triggers any scenario transitions."""
    return await engine.check_progression(request.session_id, request.user_input)


@router.post("/transition", status_code=status.HTTP_200_OK)
async def transition_scenario(
    request: TransitionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Manually transition the scenario to a new Act or Sequence."""
    await engine.execute_transition(
        request.session_id, request.next_act_id, request.next_seq_id
    )
    return {"status": "success"}
