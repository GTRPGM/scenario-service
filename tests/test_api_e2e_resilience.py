from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.core.models.generation import ScenarioInjectSchema
from scenario.main import app


@pytest.fixture
def dirty_llm_response():
    """LLM이 내뱉는 최악의 중첩 데이터 시뮬레이션"""
    return {
        "plan": {
            "title": "Dirty E2E Test",
            "total_summary": "Summary",
            "description": "Desc",
            "acts": [
                {
                    "id": "act_1",
                    "name": "First Act",
                    "description": "D",
                    "goal": "G",
                    "exit_criteria": "E",
                    "sequences": [
                        {"id": "seq_1_1", "name": "Inside Act Dict"},
                        {"id": "seq_1_2", "name": "Another Dict"},
                    ],
                }
            ],
            "relations": [],
        },
        "items": [],
        "npcs": [],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "seq_1_1",
                    "name": "S1",
                    "description": "D1",
                    "goal": "G1",
                    "exit_triggers": [],
                    "location_name": "L1",
                },
                {
                    "id": "seq_1_2",
                    "name": "S2",
                    "description": "D2",
                    "goal": "G2",
                    "exit_triggers": [],
                    "location_name": "L2",
                },
            ]
        },
    }


def test_api_generate_pure_resilience(dirty_llm_response, mock_repository):
    """
    API 호출 시 LLM이 지저분한 데이터를 주더라도
    엔진이 이를 정제하여 201 응답과 함께 올바른 스키마를 반환하는지 테스트
    """
    # 1. 실제 엔진 생성 (로직 포함)
    mock_writer_graph = AsyncMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run.return_value = dirty_llm_response

    real_engine = ScenarioEngine(repository=mock_repository, writer=mock_writer_graph)

    # 2. FastAPI 의존성 오버라이드
    app.dependency_overrides[get_scenario_engine] = lambda: real_engine
    client = TestClient(app)

    # 3. API 호출
    response = client.post("/api/v1/generation/pure", json={"concept": "test concept"})

    # 4. 검증
    assert response.status_code == 201
    result_data = response.json()["data"]

    # Acts 내부의 sequences가 반드시 문자열 리스트여야 함
    for act in result_data["acts"]:
        for seq_id in act["sequences"]:
            assert isinstance(seq_id, str), f"Expected string ID, got {type(seq_id)}"
            assert seq_id, "Expected non-empty sequence ID"

    # 최종 결과가 스키마를 통과하는지 재확인
    ScenarioInjectSchema.model_validate(result_data)

    app.dependency_overrides.clear()
