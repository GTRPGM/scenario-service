from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from scenario.core.deps import get_scenario_engine, get_validator_agent
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.models.generation import ValidationOutput
from scenario.plugins.agent.scenario_agents import ValidatorAgent

router = APIRouter()


class ValidationRequest(BaseModel):
    scenario_id: str
    act_id: str
    seq_id: str
    user_input: str


class SessionCheckRequest(BaseModel):
    scenario_id: str
    session_id: str
    user_input: str


@router.post("/validate", response_model=ValidationOutput)
async def validate_by_ids(
    request: ValidationRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
    validator: Annotated[ValidatorAgent, Depends(get_validator_agent)],
):
    """Validate progression using explicit scenario, act, and sequence IDs."""
    try:
        result = await engine.validate_progression(
            scenario_id=request.scenario_id,
            act_id=request.act_id,
            seq_id=request.seq_id,
            user_input=request.user_input,
            validator_agent=validator,
        )
        return ValidationOutput(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/session", response_model=ValidationOutput)
async def validate_by_session(
    request: SessionCheckRequest,
    engine: Annotated[ScenarioEngine, Depends(get_scenario_engine)],
    validator: Annotated[ValidatorAgent, Depends(get_validator_agent)],
):
    """Validate progression by automatically retrieving state from session ID."""
    try:
        session_id_uuid = UUID(request.session_id)
        session_state = await engine.get_session_state(session_id_uuid)
        if not session_state:
            raise ValueError(f"Session {request.session_id} not found")

        # Use scenario_id from request as priority (GM sends it)
        scenario_id = request.scenario_id or str(session_state.get("scenario_id"))
        act_id = session_state.get("current_act_id")
        seq_id = session_state.get("current_sequence_id")

        if not all([scenario_id, act_id, seq_id]):
            raise ValueError("Incomplete session state")

        result = await engine.validate_progression(
            scenario_id=scenario_id,
            act_id=act_id,
            seq_id=seq_id,
            user_input=request.user_input,
            validator_agent=validator,
        )

        # Add session_id to the response
        result["session_id"] = request.session_id
        return ValidationOutput(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
