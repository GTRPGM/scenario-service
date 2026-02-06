from unittest.mock import MagicMock

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.plugins.db.adapter import PostgresScenarioAdapter


def _build_engine() -> ScenarioEngine:
    return ScenarioEngine(repository=MagicMock(), writer=MagicMock())


def test_package_scenario_uses_canonical_entity_fields() -> None:
    engine = _build_engine()
    state = {
        "plan": {
            "title": "Canonical",
            "acts": [
                {
                    "id": "act-1",
                    "name": "Act 1",
                    "goal": "G",
                    "exit_criteria": "E",
                    "sequences": ["seq-1"],
                }
            ],
            "relations": [],
        },
        "content": {
            "sequences": [
                {
                    "id": "seq-1",
                    "name": "S1",
                    "location_name": "L1",
                    "description": "D",
                    "goal": "G",
                    "npcs": ["npc-1"],
                    "enemies": ["enemy-1"],
                    "items": ["item-1001"],
                }
            ]
        },
        "npcs": [{"scenario_npc_id": "npc-1", "name": "N", "master_id": "1001"}],
        "enemies": [{"scenario_enemy_id": "enemy-1", "name": "E", "master_id": "2001"}],
        "items": [{"item_id": 1001, "name": "I", "master_id": "3001"}],
    }

    packaged = engine._package_scenario(state)

    assert "scenario_item_id" in packaged["items"][0]
    assert "rule_id" in packaged["items"][0]
    assert "rule_id" in packaged["npcs"][0]
    assert "rule_id" in packaged["enemies"][0]
    assert packaged["items"][0]["scenario_item_id"] == "101"
    assert packaged["items"][0]["rule_id"] == 3001


def test_to_state_payload_rejects_broken_references() -> None:
    engine = _build_engine()
    bad_payload = {
        "title": "Broken",
        "acts": [
            {
                "id": "act-1",
                "name": "A",
                "exit_criteria": "E",
                "sequences": ["seq-404"],
            }
        ],
        "sequences": [],
        "npcs": [],
        "enemies": [],
        "items": [],
        "relations": [],
    }

    with pytest.raises(ValueError, match="act\\[act-1\\]"):
        engine._to_state_injection_payload(bad_payload)


def test_adapter_rejects_invalid_sequence_item_reference() -> None:
    adapter = PostgresScenarioAdapter(db=MagicMock(), loader=MagicMock())
    bad = {
        "acts": [{"id": "act-1", "sequences": ["seq-1"]}],
        "sequences": [{"id": "seq-1", "items": ["missing-item"]}],
        "items": [{"scenario_item_id": "101", "name": "I"}],
        "npcs": [],
        "enemies": [],
        "relations": [],
    }

    with pytest.raises(ValueError, match="sequence\\[seq-1\\]\\.items"):
        adapter._validate_payload_references(bad)
