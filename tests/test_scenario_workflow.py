# tests/test_scenario_workflow.py

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.plugins.db.adapter import PostgresScenarioAdapter


@pytest.fixture
def mock_data():
    return {
        "plan": {
            "title": "Test Scenario",
            "description": "Long Desc",
            "total_summary": "Summary",
            "difficulty": "normal",
            "genre": "fantasy",
            "tags": ["test"],
            "total_acts": 1,
            "acts": [
                {
                    "id": "act-1",
                    "name": "Act 1",
                    "goal": "Goal 1",
                    "sequences": ["seq-1"],
                }
            ],
            "relations": [
                {
                    "from_id": "npc-1",
                    "to_id": "enemy-1",
                    "relation_type": "foe",
                    "affinity": 0,
                    "meta": {"reason": "grudge"},
                }
            ],
        },
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "Seq 1",
                    "sequence_type": "combat",
                    "location_name": "Cave",
                    "location_theme": "dark",
                    "location_description": "A dark cave",
                    "description": "Exploring...",
                    "goal": "Survive",
                    "exit_triggers": ["kill_boss"],
                    "npcs": [
                        {
                            "scenario_npc_id": "npc-1",
                            "name": "Ally",
                            "description": "Helpful",
                            "state": {"numeric": {"HP": 10}, "boolean": {}},
                        }
                    ],
                    "enemies": [
                        {
                            "scenario_enemy_id": "enemy-1",
                            "name": "Boss",
                            "description": "Strong",
                            "state": {"numeric": {"HP": 100}, "boolean": {}},
                        }
                    ],
                    "items": [
                        {
                            "item_id": "550e8400-e29b-41d4-a716-446655440001",
                            "name": "Sword",
                            "description": "Sharp",
                            "item_type": "weapon",
                            "meta": {"power": 10},
                        }
                    ],
                }
            ]
        },
    }


@pytest.mark.asyncio
async def test_engine_aggregation_logic(mock_data):
    """1단계: 엔진이 Planner/Writer 결과를 올바르게 취합하여 Repository로 전달하는지 검증"""
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock()

    mock_writer = MagicMock(spec=ScenarioWriterGraph)
    mock_writer.run = AsyncMock(return_value=mock_data)

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer)
    await engine.generate_scenario("concept")

    # save_scenario 호출 인자 검증
    args, _ = mock_repo.save_scenario.call_args
    data = args[2]

    assert data["title"] == "Test Scenario"
    assert len(data["npcs"]) == 1
    assert len(data["enemies"]) == 1
    assert len(data["relations"]) == 1
    assert data["relations"][0]["from_id"] == "npc-1"


@pytest.mark.asyncio
async def test_db_adapter_query_calls(mock_data):
    """2단계: DB 어댑터가 취합된 데이터를 바탕으로 올바른 Cypher 쿼리들을 실행하는지 검증"""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()

    mock_loader = MagicMock()
    mock_loader.load_cypher.side_effect = lambda name: f"QUERY_{name}"

    adapter = PostgresScenarioAdapter(db=mock_db, loader=mock_loader)

    scenario_id = uuid4()
    await adapter.save_scenario(
        scenario_id, "concept", {**mock_data["plan"], **mock_data["content"]}
    )

    # 실행된 쿼리들 확인
    executed_queries = [call.args[0] for call in mock_db.execute.call_args_list]

    assert "QUERY_create_scenario_base" in executed_queries
    assert "QUERY_create_act" in executed_queries
    assert "QUERY_create_sequence" in executed_queries
    assert "QUERY_create_entity" in executed_queries
    assert "QUERY_create_relation" in executed_queries

    # Relation 쿼리의 파라미터 확인
    rel_call = [
        call
        for call in mock_db.execute.call_args_list
        if call.args[0] == "QUERY_create_relation"
    ][0]
    import json

    rel_params = json.loads(rel_call.args[1])
    assert rel_params["from_id"] == "npc-1"
    assert rel_params["relation_type"] == "foe"
