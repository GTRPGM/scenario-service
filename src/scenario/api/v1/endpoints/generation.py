from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine

router = APIRouter()


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
