# src/scenario/api/v1/endpoints/scenario.py

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
    """
    Validate if the user action triggers a progression in the scenario.
    The engine will fetch necessary act/sequence context automatically.
    """
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


class GenerateScenarioRequest(BaseModel):
    concept: str


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_pure(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Pure generation based on topic only."""
    return await engine.generate_pure(request.concept)


@router.post("/ground", status_code=status.HTTP_201_CREATED)
async def generate_grounded(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Generate first, then delegate grounding to Rule Engine."""
    return await engine.generate_grounded(request.concept)


@router.post("/info", status_code=status.HTTP_201_CREATED)
async def generate_informed(
    request: GenerateScenarioRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Generate first, then match with all assets locally."""
    return await engine.generate_informed(request.concept)


@router.get("/", response_model=List[Dict])
async def list_scenarios(
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """List all saved scenario templates."""
    return await engine.list_scenarios()


@router.post("/{scenario_id}/inject", status_code=status.HTTP_200_OK)
async def inject_scenario(
    scenario_id: UUID,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
):
    """Inject a generated scenario into the State Manager."""
    try:
        return await engine.inject_to_state_manager(scenario_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        detail = f"Injection failed: {str(e)}"
        raise HTTPException(status_code=500, detail=detail) from e
