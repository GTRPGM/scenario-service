# src/scenario/api/v1/endpoints/scenario.py

from typing import Annotated, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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


class GenerateScenarioRequest(BaseModel):
    concept: str


class InitializeSessionRequest(BaseModel):
    session_id: UUID
    scenario_id: UUID


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_scenario(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Trigger the multi-agent generation pipeline."""
    return await engine.generate_scenario(request.concept)


@router.get("/", response_model=List[Dict])
async def list_scenarios(
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """List all saved scenario templates."""
    return await engine.list_scenarios()


@router.post("/session/initialize", status_code=status.HTTP_201_CREATED)
async def initialize_session(
    request: InitializeSessionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Create a new session instance from a scenario template."""
    try:
        return await engine.initialize_session(request.session_id, request.scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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


@router.get("/sessions/list", response_model=List[Dict])
async def list_sessions(
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """List all active player sessions."""
    return await engine.repository.list_sessions()
