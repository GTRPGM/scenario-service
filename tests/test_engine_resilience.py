import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine


@pytest.fixture
def engine(mock_repository):
    from unittest.mock import MagicMock

    from scenario.core.engine.writer_graph import ScenarioWriterGraph

    return ScenarioEngine(
        repository=mock_repository, writer=MagicMock(spec=ScenarioWriterGraph)
    )


def test_engine_resilience_to_nested_objects(engine: ScenarioEngine):
    """
    LLM이 ID 리스트 자리에 객체 리스트를 넘겨주는 최악의 상황에서도
    엔진이 ID만 잘 추출하여 평면 구조를 만드는지 검증합니다.
    """
    dirty_state = {
        "plan": {
            "title": "Dirty Data Test",
            "acts": [
                {
                    "id": "act_initial",
                    "name": "Act 1",
                    "sequences": [
                        {"id": "poi_1", "name": "Location 1"},
                        {"id": "poi_2", "name": "Location 2"},
                    ],
                }
            ],
        },
        "items": [],
        "npcs": [],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "poi_1",
                    "name": "L1",
                    "description": "D1",
                    "location_name": "Loc 1",
                },
                {
                    "id": "poi_2",
                    "name": "L2",
                    "description": "D2",
                    "location_name": "Loc 2",
                },
            ]
        },
    }

    # 실행
    packaged = engine._package_scenario(dirty_state)

    # 검증: acts 내부의 sequences는 반드시 문자열 리스트여야 함
    cleaned_sequences = packaged["acts"][0]["sequences"]
    assert cleaned_sequences == ["seq-1", "seq-2"]
    assert isinstance(cleaned_sequences[0], str)


def test_engine_id_extraction_logic(engine: ScenarioEngine):
    """다양한 형태의 ID가 들어와도 시스템 아이디로 잘 매핑하는지 확인"""
    state = {
        "plan": {
            "title": "T",
            "acts": [
                {
                    "id": "act-101",
                    "name": "A",
                    "sequences": ["s1"],
                    "goal": "G",
                    "exit_criteria": "E",
                    "region_name": "R",
                }
            ],
            "relations": [{"from_id": "n1", "to_id": "n2"}],
        },
        "items": [{"item_id": "i1", "name": "I"}],
        "npcs": [
            {"scenario_npc_id": "n1", "name": "N1"},
            {"scenario_npc_id": "n2", "name": "N2"},
        ],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "s1",
                    "name": "S",
                    "npcs": ["n1", "n2"],
                    "items": ["i1"],
                    "location_name": "L",
                    "description": "D",
                    "goal": "G",
                }
            ]
        },
    }
    packaged = engine._package_scenario(state)

    assert packaged["acts"][0]["id"] == "act-1"
    assert packaged["sequences"][0]["id"] == "seq-1"
    assert packaged["sequences"][0]["npcs"][0] == "npc-1"
    assert packaged["sequences"][0]["items"][0] == "item-101"

    # Relations: n1 -> n2 should map to npc-1 -> npc-2
    assert packaged["relations"][0]["from_id"] == "npc-1"
    assert packaged["relations"][0]["to_id"] == "npc-2"
