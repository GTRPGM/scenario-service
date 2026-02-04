import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.models.generation import ScenarioInjectSchema


async def debug_packaging():
    # Mock dependencies
    mock_repo = MagicMock()
    mock_repo.save_scenario = AsyncMock(return_value="mock-uuid")
    mock_writer = MagicMock()

    engine = ScenarioEngine(repository=mock_repo, writer=mock_writer)

    # Sample state that LLM might produce (unnormalized IDs, flat catalogs)
    state = {
        "plan": {
            "title": "Debug Forest",
            "total_summary": "A small forest test",
            "description": "Longer description",
            "acts": [
                {
                    "id": "act_initial",
                    "name": "The Beginning",
                    "region_name": "Forest Edge",
                    "description": "Start of the journey",
                    "goal": "Enter the forest",
                    "exit_criteria": "Find the path",
                    "sequences": ["seq_001"],
                }
            ],
            "relations": [
                {
                    "from_id": "npc_wolf_alpha",
                    "to_id": "item_key_01",
                    "relation_type": "guards",
                }
            ],
        },
        "items": [
            {
                "item_id": "item_key_01",
                "name": "Silver Key",
                "description": "A shiny key",
                "item_type": "key",
            }
        ],
        "npcs": [
            {
                "scenario_npc_id": "npc_wolf_alpha",
                "name": "Alpha Wolf",
                "description": "A large scary wolf",
                "tags": ["enemy", "beast"],
            }
        ],
        "enemies": [],
        "content": {
            "sequences": [
                {
                    "id": "seq_001",
                    "name": "Wolf Encounter",
                    "location_name": "Wolf Den",
                    "npcs": ["npc_wolf_alpha"],
                    "items": ["item_key_01"],
                    "description": "You see a wolf.",
                    "goal": "Get the key",
                }
            ]
        },
    }

    print("=== PACKAGING START ===")
    packaged = engine._package_scenario(state)

    print("\n=== PACKAGED DATA (NESTED STRUCTURE) ===")
    print(json.dumps(packaged, indent=2, ensure_ascii=False))

    # Validate with Schema
    try:
        ScenarioInjectSchema.model_validate(packaged)
        print("\n✅ Schema Validation Passed!")
    except Exception as e:
        print(f"\n❌ Schema Validation Failed: {e}")


if __name__ == "__main__":
    asyncio.run(debug_packaging())
