from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine


@pytest.fixture
def engine():
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value="test-uuid")
    return ScenarioEngine(repository=mock_repo, writer=MagicMock())


def test_package_scenario_id_normalization(engine):
    state = {
        "plan": {
            "title": "Test",
            "acts": [
                {"id": "act-1", "name": "Act 1", "goal": "G", "sequences": ["seq-1"]}
            ],
            "relations": [
                {"from_id": "npc-01", "to_id": "npc-02", "relation_type": "friend"}
            ],
        },
        "items": [{"item_id": "item-007", "name": "Bond Gun"}],
        "npcs": [
            {"scenario_npc_id": "npc-01", "name": "James"},
            {"scenario_npc_id": "npc-02", "name": "M"},
        ],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "S1",
                    "location_name": "L1",
                    "location_theme": "T1",
                    "location_description": "D1",
                    "description": "D",
                    "npcs": ["npc-01"],
                    "items": ["item-007"],
                }
            ]
        },
    }

    packaged = engine._package_scenario(state)

    # Sequence Reference normalization
    seq = packaged["sequences"][0]
    assert seq["id"] == "seq-1"

    # Flat reference normalization
    assert seq["npcs"][0] == "npc-1"
    assert seq["items"][0] == "101"

    # Relation ID normalization
    rel = packaged["relations"][0]
    assert rel["from_id"] == "npc-1"
    assert rel["to_id"] == "npc-2"


def test_package_scenario_contract_with_db_adapter(engine):
    """
    핵심 로직인 master_id, summary, goal 등이 패키징 결과물에
    정확히 포함되어 있는지 검증합니다.
    """
    state = {
        "plan": {
            "title": "T",
            "total_summary": "S",
            "description": "D",
            "acts": [
                {
                    "id": "act-1",
                    "name": "A",
                    "region_name": "R",
                    "description": "D",
                    "goal": "G",
                    "exit_criteria": "E",
                    "sequences": ["seq-1"],
                }
            ],
            "relations": [],
        },
        "items": [{"item_id": 1001, "name": "I", "master_id": "M-1"}],
        "npcs": [{"scenario_npc_id": "npc-1", "name": "N", "master_id": "M-2"}],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "S",
                    "location_name": "L",
                    "location_master_id": "LM-1",
                    "location_theme": "T",
                    "location_description": "D",
                    "danger_min": 1,
                    "danger_max": 10,
                    "description": "D",
                    "goal": "G",
                    "exit_triggers": [],
                    "npcs": ["npc-1"],
                    "enemies": [],
                    "items": [1001],
                }
            ]
        },
    }

    packaged = engine._package_scenario(state)

    # 1. Base Fields
    assert "summary" in packaged
    assert packaged["summary"] == "S"

    # 2. Act Fields
    act = packaged["acts"][0]
    assert "region_name" in act
    assert "goal" in act
    assert act["goal"] == "G"

    # 3. Sequence Fields
    seq = packaged["sequences"][0]
    assert "location_master_id" in seq
    assert "danger_min" in seq
    assert seq["location_master_id"] == "LM-1"

    # 4. Entity catalog master_id Preservation
    item = next(i for i in packaged["items"] if i["item_id"] == 101)
    assert item["master_id"] == "M-1"

    npc = next(n for n in packaged["npcs"] if n["scenario_npc_id"] == "npc-1")
    assert npc["master_id"] == "M-2"
