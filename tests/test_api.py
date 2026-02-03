from unittest.mock import MagicMock, patch
from uuid import uuid4


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
    payload = {"session_id": session_id, "next_act_id": "act_2", "next_seq_id": "seq_5"}
    response = client.post("/api/v1/manage/sessions/transition", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_generate_scenario_endpoint(client):
    payload = {"concept": "Space opera in a dying galaxy"}
    response = client.post("/api/v1/generation/pure", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "success"
