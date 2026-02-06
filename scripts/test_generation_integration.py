import argparse
import asyncio
import json
import os
import sys
from typing import Optional

# Add src to sys.path to import local modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.models.generation import ScenarioInjectSchema


async def run_integration_test(
    concept: str, use_real_llm: bool = False, gateway_host: Optional[str] = None
):
    print(f"\n🚀 {'REAL LLM' if use_real_llm else 'MOCK'} Integration Test Start")
    print(f"Concept: {concept}")

    if use_real_llm:
        if gateway_host:
            os.environ["LLM_GATEWAY_HOST"] = gateway_host
            print(f"Using LLM Gateway: {gateway_host}")

        engine = await get_scenario_engine()
        try:
            # 1. Generate
            result = await engine.generate_pure(concept)
            scenario_id = result["scenario_id"]
            print(f"\n✅ Generation Success! Internal ID: {scenario_id}")

            # 2. Inject (This will now also save the mapping if SM responds)
            print("\nAttempting injection to State Manager...")
            try:
                inject_res = await engine.inject_to_state_manager(scenario_id)
                print(
                    f"✅ Injection Result: "
                    f"{json.dumps(inject_res, indent=2, ensure_ascii=False)}"
                )
            except Exception as e:
                print(
                    f"⚠️ Injection skipped or failed (State Manager might be offline): "
                    f"{e}"
                )

        except Exception as e:
            print(f"\n❌ Generation Failed: {e}")
            sys.exit(1)
    else:
        # Mock mode for logic verification (similar to debug_packaging.py)
        from unittest.mock import AsyncMock, MagicMock

        mock_repo = MagicMock()
        mock_repo.save_scenario = AsyncMock(return_value="mock-uuid")
        mock_writer = MagicMock()

        engine = ScenarioEngine(repository=mock_repo, writer=mock_writer)

        # Test basic packaging logic with unnormalized data
        state = {
            "plan": {
                "title": "Test",
                "acts": [
                    {
                        "id": "A1",
                        "name": "Act 1",
                        "sequences": ["S1"],
                        "goal": "G",
                        "exit_criteria": "E",
                        "region_name": "R",
                    }
                ],
            },
            "items": [{"item_id": "999", "name": "Sword"}],
            "npcs": [{"scenario_npc_id": "N-001", "name": "Guardian"}],
            "enemies": [],
            "content": {
                "sequences": [
                    {
                        "id": "S1",
                        "name": "Seq 1",
                        "npcs": ["N-001"],
                        "items": ["999"],
                        "description": "D",
                        "goal": "G",
                        "location_name": "L",
                    }
                ]
            },
        }

        packaged = engine._package_scenario(state)
        print("\n=== Packaged Data (Logic Check) ===")
        print(json.dumps(packaged, indent=2, ensure_ascii=False))

        try:
            ScenarioInjectSchema.model_validate(packaged)
            print("\n✅ Logic & Schema Validation Passed!")
        except Exception as e:
            print(f"\n❌ Schema Validation Failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scenario Generation Integration Test")
    parser.add_argument(
        "--concept",
        type=str,
        default="A dark dungeon with a silver key",
        help="Scenario concept",
    )
    parser.add_argument("--real", action="store_true", help="Use real LLM Gateway")
    parser.add_argument(
        "--host", type=str, default="35.216.98.244", help="LLM Gateway Host IP"
    )

    args = parser.parse_args()

    asyncio.run(run_integration_test(args.concept, args.real, args.host))
