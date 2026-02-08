from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx


def test_basic_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_services_health_check(client):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        response = client.get("/api/v1/system/services/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "llm_gateway" in response.json()


def test_check_progression_endpoint(client):
    session_id = str(uuid4())
    scenario_id = str(uuid4())
    payload = {
        "scenario_id": scenario_id,
        "session_id": session_id,
        "user_input": "I want to talk to the guard",
    }
    response = client.post("/api/v1/check/session", json=payload)
    assert response.status_code in [200, 404]


def test_transition_endpoint(client):
    session_id = str(uuid4())
    payload = {
        "session_id": session_id,
        "next_act_id": "act_2",
        "next_seq_id": "seq_5",
    }

    with patch("httpx.AsyncClient.put", new_callable=AsyncMock) as mock_put:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "status": "success",
            "data": {
                "session_id": session_id,
                "current_act_id": "act-2",
                "current_sequence_id": "seq-5",
            },
        }
        mock_put.return_value = mock_resp

        response = client.post("/api/v1/manage/sessions/transition", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["current_act_id"] == "act-2"
        assert response.json()["data"]["current_sequence_id"] == "seq-5"

        called_url = mock_put.await_args.args[0]
        called_json = mock_put.await_args.kwargs["json"]
        assert called_url.endswith(f"/state/session/{session_id}/act")
        assert called_json == {
            "new_act": 2,
            "new_act_id": "act-2",
            "new_sequence_id": "seq-5",
        }


def test_transition_sequence_only_endpoint(client):
    session_id = str(uuid4())
    payload = {
        "session_id": session_id,
        "next_seq_id": "seq_3",
    }

    with patch("httpx.AsyncClient.put", new_callable=AsyncMock) as mock_put:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "status": "success",
            "data": {
                "session_id": session_id,
                "current_sequence_id": "seq-3",
            },
        }
        mock_put.return_value = mock_resp

        response = client.post("/api/v1/manage/sessions/transition", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["current_sequence_id"] == "seq-3"

        called_url = mock_put.await_args.args[0]
        called_json = mock_put.await_args.kwargs["json"]
        assert called_url.endswith(f"/state/session/{session_id}/sequence")
        assert called_json == {
            "new_sequence": 3,
            "new_sequence_id": "seq-3",
        }


def test_transition_invalid_sequence_id_returns_400(client):
    session_id = str(uuid4())
    payload = {
        "session_id": session_id,
        "next_seq_id": "not-a-seq",
    }

    response = client.post("/api/v1/manage/sessions/transition", json=payload)
    assert response.status_code == 400
    assert "Invalid seq_id format" in response.json()["detail"]


def test_generate_scenario_endpoint(client):
    payload = {"concept": "Space opera in a dying galaxy"}
    response = client.post("/api/v1/generation/pure", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "success"


def test_debug_inject_save_endpoint(client):
    payload = {
        "payload": {
            "title": "DEBUG_SCENARIO",
            "acts": [{"id": "act-1", "name": "A1", "sequences": ["seq-1"]}],
            "sequences": [
                {"id": "seq-1", "name": "S1", "npcs": [], "enemies": [], "items": []}
            ],
            "npcs": [],
            "enemies": [],
            "items": [],
            "relations": [],
        },
        "inject_to_state": False,
    }

    with patch(
        "scenario.core.engine.scenario_engine.ScenarioEngine.save_and_inject_debug",
        new_callable=AsyncMock,
    ) as mock_debug:
        mock_debug.return_value = {
            "status": "success",
            "scenario_service_id": str(uuid4()),
            "saved": True,
            "injected": False,
        }
        response = client.post(
            "/api/v1/manage/scenarios/debug/inject-save", json=payload
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["saved"] is True


def test_debug_inject_save_endpoint_state_inject_failure(client):
    payload = {"payload": {"title": "DEBUG_SCENARIO"}, "inject_to_state": True}

    with patch(
        "scenario.core.engine.scenario_engine.ScenarioEngine.save_and_inject_debug",
        new_callable=AsyncMock,
    ) as mock_debug:
        req = httpx.Request("POST", "http://state-manager/state/scenario/inject")
        res = httpx.Response(500, request=req)
        mock_debug.side_effect = httpx.HTTPStatusError(
            "state inject failed",
            request=req,
            response=res,
        )
        response = client.post(
            "/api/v1/manage/scenarios/debug/inject-save", json=payload
        )
        assert response.status_code == 502
