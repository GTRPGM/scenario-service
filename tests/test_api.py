# tests/test_api.py

from uuid import uuid4


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_check_progression_endpoint(client):
    session_id = str(uuid4())
    payload = {"session_id": session_id, "user_input": "I want to talk to the guard"}
    response = client.post("/api/v1/scenario/check", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_transition_endpoint(client):
    session_id = str(uuid4())
    payload = {"session_id": session_id, "next_act_id": "act_2", "next_seq_id": "seq_5"}
    response = client.post("/api/v1/scenario/transition", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_generate_scenario_endpoint(client):
    payload = {"concept": "Space opera in a dying galaxy"}
    response = client.post("/api/v1/scenario/generate", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
