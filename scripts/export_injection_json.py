import asyncio
import json
import os
import sys
from uuid import UUID

from testcontainers.postgres import PostgresContainer

# 1. Do NOT import scenario modules at top level
# sys.path.append must happen before inner imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))


class PostgresExContainer(PostgresContainer):
    def __init__(self, image="postgres-ex:latest", **kwargs):
        super().__init__(image, **kwargs)
        self.with_exposed_ports(5432)


async def export_json_with_container(
    concept: str, output_path: str = "injection_payload.json"
):
    print("🚀 Starting Local TestContainer (postgres-ex) with shm_size=2g...")

    with PostgresExContainer(shm_size="2g") as postgres:
        host = postgres.get_container_host_ip()
        port = postgres.get_exposed_port(5432)

        # 2. Inject Environment Variables BEFORE any scenario imports
        os.environ["DB_HOST"] = str(host)
        os.environ["DB_PORT"] = str(port)
        os.environ["DB_USER"] = str(postgres.username)
        os.environ["DB_PASSWORD"] = str(postgres.password)
        os.environ["DB_NAME"] = str(postgres.dbname)

        # Explicitly set LLM Gateway Host for remote access (Forced as requested)
        os.environ["LLM_GATEWAY_HOST"] = "35.216.98.244"

        print(f"🔗 DB Container started at {host}:{port}")
        print(f"📡 LLM Gateway Host: {os.environ.get('LLM_GATEWAY_HOST', 'NOT SET')}")

        # 3. Inner imports so settings pick up the injected env vars
        from scenario.core.deps import db_handler, get_scenario_engine
        from scenario.core.models.generation import ScenarioInjectSchema
        from scenario.infra.db.init_db import init_db

        # 3. Initialize DB schema explicitly in the container
        print("🛠️ Initializing DB Schema (SQL + Graph)...")
        await init_db(db_handler)

        engine = await get_scenario_engine()

        try:
            import psutil

            # Disk I/O Measurement Before
            io_before = psutil.disk_io_counters()

            print(f"✍️ [Process] Requesting LLM generation for: '{concept}'")
            gen_res = await engine.generate_pure(concept)
            print("✅ [Process] LLM Response received!")

            # Disk I/O Measurement After
            io_after = psutil.disk_io_counters()
            write_diff = io_after.write_bytes - io_before.write_bytes
            print(
                f"📊 [Disk IO] Total System Write during DB Save: "
                f"{write_diff / 1024 / 1024:.2f} MB"
            )

            scenario_id = UUID(gen_res["scenario_id"])

            # 4. Get Full Graph from Local DB
            raw_data = await engine.repository.get_scenario_full_graph(scenario_id)

            # 5. Validate and Dump
            print("\n🔍 Validating payload against State Manager requirements...")
            try:
                validated_data = ScenarioInjectSchema.model_validate(raw_data)
                payload = validated_data.model_dump()
                payload["scenario_id"] = str(scenario_id)
                print("✅ Payload is COMPATIBLE with State Manager!")
            except Exception as ve:
                print(f"❌ COMPATIBILITY ERROR: {ve}")
                payload = raw_data
                payload["scenario_id"] = str(scenario_id)

            # 6. Save to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

            print(f"\n📂 Final Injection JSON saved to: {output_path}")

        except Exception as e:
            print(f"❌ Export failed: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    concept = sys.argv[1] if len(sys.argv) > 1 else "Ancient Ruins of Galthar"
    asyncio.run(export_json_with_container(concept))
