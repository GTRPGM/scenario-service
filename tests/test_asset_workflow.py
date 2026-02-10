from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph


@pytest.mark.asyncio
async def test_full_asset_workflow_aggregation():
    """
    Test alignment with new nested structure:
    - Items are nested in sequences
    - IDs are managed by system (item-1, etc.)
    """
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value=uuid4())

    mock_plan = {
        "title": "Aligned Dungeon",
        "description": "Desc",
        "difficulty": "normal",
        "genre": "fantasy",
        "tags": [],
        "total_acts": 1,
        "acts": [
            {
                "id": "act-1",
                "name": "Act 1",
                "region_name": "Region",
                "description": "Region Desc",
                "goal": "Goal",
                "exit_criteria": "Exit",
                "sequences": ["seq-1"],
            }
        ],
        "item_manifest": [{"id": "1001", "name": "Item", "concept": "C"}],
        "npc_manifest": [{"id": "npc-1", "name": "NPC", "concept": "C"}],
        "enemy_manifest": [{"id": "enemy-2", "name": "Enemy", "concept": "C"}],
        "total_summary": "Summary",
        "relations": [
            {"from_id": "enemy-2", "to_id": "1001", "relation_type": "ownership"}
        ],
    }

    mock_items = [
        {
            "item_id": 1001,
            "name": "Sword",
            "description": "D",
            "item_type": "equipment",
            "meta": {},
        }
    ]
    mock_npcs = [
        {
            "scenario_npc_id": "npc-1",
            "name": "Ghost",
            "description": "D",
            "tags": [],
            "state": {},
        }
    ]
    mock_enemies = [
        {
            "scenario_enemy_id": "enemy-2",
            "name": "Skeleton",
            "description": "D",
            "tags": [],
            "state": {},
            "dropped_items": ["1001"],
        }
    ]

    mock_content = {
        "sequences": [
            {
                "id": "seq-1",
                "name": "Entrance",
                "sequence_type": "Exploration",
                "location_name": "Gate",
                "location_theme": "stone",
                "location_description": "D",
                "description": "D",
                "goal": "G",
                "exit_triggers": [],
                "npcs": ["npc-1"],
                "enemies": ["enemy-2"],
                "items": ["1001"],
            }
        ]
    }

    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    mock_writer_graph.run = AsyncMock(
        return_value={
            "plan": mock_plan,
            "items": mock_items,
            "npcs": mock_npcs,
            "enemies": mock_enemies,
            "content": mock_content,
            "is_consistent": True,
        }
    )
    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer_graph)
    result = await engine.generate_scenario("Concept")

    data = result["data"]

    # Assert Flat Structure (references only)
    seq = data["sequences"][0]
    assert seq["items"][0] == "101"
    assert seq["npcs"][0] == "npc-1"
    assert seq["enemies"][0] == "enemy-1"

    # Check catalogs for actual data
    item = next(i for i in data["items"] if i["scenario_item_id"] == "101")
    assert item["name"] == "Sword"

    npc = next(n for n in data["npcs"] if n["scenario_npc_id"] == "npc-1")
    assert npc["name"] == "Ghost"

    enemy = next(e for e in data["enemies"] if e["scenario_enemy_id"] == "enemy-1")
    assert enemy["name"] == "Skeleton"
    # No rule_id/master_id provided in mock_enemies, normalized to 0
    assert enemy["rule_id"] == 0

    # Verify relations instead of dropped_items field
    drop_rel = next(
        r
        for r in data["relations"]
        if r["from_id"] == "enemy-1" and r["to_id"] == "101"
    )
    assert drop_rel["relation_type"] == "ownership"


@pytest.mark.asyncio
async def test_informed_generation_grounding():
    """
    Test generate_informed logic with nested structure.
    """
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value=uuid4())

    mock_writer_graph = MagicMock()
    # Mock data with ungrounded assets
    mock_writer_graph.run = AsyncMock(
        return_value={
            "plan": {"title": "T", "acts": [], "relations": []},
            "items": [{"item_id": 1001, "name": "Excalibur", "meta": {}}],
            "npcs": [],
            "enemies": [],
            "content": {
                "sequences": [
                    {
                        "id": "seq-1",
                        "name": "S",
                        "description": "D",
                        "goal": "G",
                        "location_name": "L",
                        "items": [1001],
                    }
                ]
            },
        }
    )

    mock_rule_engine = AsyncMock()
    mock_rule_engine.get_all_assets = AsyncMock(
        return_value={
            "items": [
                {
                    "master_id": "99999",
                    "name": "Excalibur",
                    "base_price": 5000,
                    "weight": 5,
                    "type": "equipment",
                }
            ]
        }
    )

    engine = ScenarioEngine(
        repository=mock_repo, writer=mock_writer_graph, rule_engine=mock_rule_engine
    )
    result = await engine.generate_informed("concept")

    data = result["data"]
    # Check item ID in sequence
    item_id = data["sequences"][0]["items"][0]
    assert item_id == "101"

    # Verify grounding in the item catalog
    item = next(i for i in data["items"] if i["scenario_item_id"] == "101")
    assert item["meta"]["price"] == 5000
    assert item["item_type"] == "equipment"
    assert item["rule_id"] == 99999
