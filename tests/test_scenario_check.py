from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_validate_by_session_success(client, mock_repository):
    # Setup
    scenario_id = "test-scenario-external-id"
    session_id = str(uuid4())
    user_input = "I open the chest"

    mock_session_state = {
        "scenario_id": str(uuid4()),
        "current_act_id": "act-1",
        "current_sequence_id": "seq-1",
    }

    # Mock repository behavior
    mock_repository.get_session_state.return_value = mock_session_state

    mock_context = {
        "act": {"name": "Act 1", "goal": "Explore", "exit_criteria": "Find key"},
        "sequences": [
            {
                "id": "seq-1",
                "name": "Sequence 1",
                "description": "A dark room",
                "goal": "Open chest",
                "exit_triggers": ["chest_opened"],
            }
        ],
    }
    mock_repository.get_act_context.return_value = mock_context

    # Execute
    payload = {
        "scenario_id": scenario_id,
        "session_id": session_id,
        "user_input": user_input,
    }
    response = client.post("/api/v1/check/session", json=payload)

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert "is_triggered" in data

    # Verify repository calls
    mock_repository.get_session_state.assert_called_once()
    # Scenario ID should be passed as provided (string)
    mock_repository.get_act_context.assert_called_once_with(scenario_id, "act-1")


@pytest.mark.asyncio
async def test_validate_by_session_not_found(client, mock_repository):
    session_id = str(uuid4())
    mock_repository.get_session_state.return_value = None  # Session not found

    payload = {
        "scenario_id": "some-scenario",
        "session_id": session_id,
        "user_input": "hello",
    }

    response = client.post("/api/v1/check/session", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
