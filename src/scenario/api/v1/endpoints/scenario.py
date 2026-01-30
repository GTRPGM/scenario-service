from typing import Annotated, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from scenario.core.deps import get_scenario_engine, get_validator_agent
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.models.generation import ValidationOutput
from scenario.plugins.agent.scenario_agents import ValidatorAgent

router = APIRouter()


class ProgressionRequest(BaseModel):
    scenario_id: str
    act_id: str
    seq_id: str
    user_input: str


@router.post("/validate-progression", response_model=ValidationOutput)
async def validate_progression(
    request: ProgressionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
    validator: Annotated[ValidatorAgent, Depends(get_validator_agent)],
):
    try:
        return await engine.validate_progression(
            scenario_id=request.scenario_id,
            act_id=request.act_id,
            seq_id=request.seq_id,
            user_input=request.user_input,
            validator_agent=validator,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class CheckProgressionRequest(BaseModel):
    session_id: str
    user_input: str


@router.post("/check", response_model=ValidationOutput)
async def check_progression_alias(
    request: CheckProgressionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
    validator: Annotated[ValidatorAgent, Depends(get_validator_agent)],
):
    try:
        session_id_uuid = UUID(request.session_id)
        session_state = await engine.get_session_state(session_id_uuid)
        if not session_state:
            raise ValueError(f"Session {request.session_id} not found")

        scenario_id = session_state.get("scenario_id")
        act_id = session_state.get("current_act_id")
        seq_id = session_state.get("current_sequence_id")

        if not all([scenario_id, act_id, seq_id]):
            raise ValueError("Incomplete session state")

        return await engine.validate_progression(
            scenario_id=str(scenario_id),
            act_id=act_id,
            seq_id=seq_id,
            user_input=request.user_input,
            validator_agent=validator,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


class TransitionRequest(BaseModel):
    session_id: str
    next_act_id: str
    next_seq_id: str


@router.post("/transition", status_code=status.HTTP_200_OK)
async def transition_session(
    request: TransitionRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    return {"status": "success"}


class GenerateScenarioRequest(BaseModel):
    concept: str


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_pure(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    return await engine.generate_pure(request.concept)


@router.post("/ground", status_code=status.HTTP_201_CREATED)
async def generate_grounded(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    return await engine.generate_grounded(request.concept)


@router.post("/info", status_code=status.HTTP_201_CREATED)
async def generate_informed(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    return await engine.generate_informed(request.concept)


@router.get("/", response_model=List[Dict])
async def list_scenarios(
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    return await engine.list_scenarios()


@router.post("/{scenario_id}/inject", status_code=status.HTTP_200_OK)
async def inject_scenario(
    scenario_id: UUID,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    try:
        return await engine.inject_to_state_manager(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        detail = f"Injection failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e
