import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from tests.scenario_models_reference import ScenarioInjectRequest


def test_packaged_data_matches_reference_request():
    """
    ScenarioEngine에서 패키징한 결과물이 tests/scenario_models_reference.py의
    ScenarioInjectRequest 규격에 완벽하게 부합하는지 테스트합니다.
    """
    from unittest.mock import MagicMock

    engine = ScenarioEngine(repository=MagicMock(), writer=MagicMock())

    # 1. 시뮬레이션된 에이전트 출력 상태
    state = {
        "plan": {
            "title": "Reference Match Test",
            "total_summary": "Summary",
            "description": "Ensuring perfect alignment",
            "acts": [
                {
                    "id": "act-1",
                    "name": "Act 1",
                    "region_name": "Cave Region",
                    "description": "D",
                    "goal": "G",
                    "exit_criteria": "E",
                    "sequences": ["seq-1"],
                }
            ],
            "relations": [
                {"from_id": "npc-1", "to_id": "item-1001", "relation_type": "possess"}
            ],
        },
        "items": [{"item_id": 1001, "name": "Sword", "description": "Sharp"}],
        "npcs": [
            {"scenario_npc_id": "npc-1", "name": "Guard", "description": "Strong"}
        ],
        "enemies": [
            {
                "scenario_enemy_id": "enemy-1",
                "name": "Goblin",
                "description": "Green",
                "dropped_items": ["1001"],
            }
        ],
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "Cave",
                    "location_name": "Dark Cave",
                    "description": "A dark place",
                    "goal": "Find light",
                    "exit_triggers": ["light_found"],
                    "npcs": ["npc-1"],
                    "enemies": ["enemy-1"],
                    "items": ["1001"],
                }
            ]
        },
    }

    # 2. 패키징 수행
    packaged = engine._package_scenario(state)

    # 3. 레퍼런스 모델로 검증 (이 단계에서 실패하면 규격 불일치)
    try:
        ref_request = ScenarioInjectRequest.model_validate(packaged)
    except Exception as e:
        pytest.fail(
            f"Packaged data does not match ScenarioInjectRequest reference: {e}"
        )

    # 4. 세부 타입 및 값 검증
    assert ref_request.title == "Reference Match Test"

    # Sequence 필드 확인
    seq = ref_request.sequences[0]
    assert seq.id == "seq-1"
    assert seq.location_name == "Dark Cave"

    # Nested NPC/Item/Enemy check (Verify presence in catalogs via packaged data)
    assert "npc-1" in seq.npcs
    assert "enemy-1" in seq.enemies
    assert "101" in seq.items

    # Catalog Data Verification
    catalog_npc = next(n for n in packaged["npcs"] if n["scenario_npc_id"] == "npc-1")
    assert catalog_npc["name"] == "Guard"

    catalog_item = next(i for i in packaged["items"] if i["item_id"] == 101)
    assert catalog_item["name"] == "Sword"

    catalog_enemy = next(
        e for e in packaged["enemies"] if e["scenario_enemy_id"] == "enemy-1"
    )
    assert catalog_enemy["name"] == "Goblin"
    assert catalog_enemy["dropped_items"] == [101]
