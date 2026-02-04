import logging
import os

import psutil
import pytest

from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.db.adapter import PostgresScenarioAdapter

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_scenario_save_and_load_real_db(real_db_handler):
    loader = QueryLoader()
    adapter = PostgresScenarioAdapter(real_db_handler, loader)

    # Disk I/O Monitoring Before
    io_before = psutil.disk_io_counters()
    proc = psutil.Process(os.getpid())
    proc_io_before = proc.io_counters().write_bytes

    concept = "Aligned DB Test"
    data = {
        "title": "DB Integrity",
        "summary": "S",
        "description": "D",
        "difficulty": "hard",
        "genre": "horror",
        "tags": [],
        "total_acts": 1,
        "acts": [
            {
                "id": "act1",
                "name": "A",
                "goal": "G",
                "region_name": "R",
                "region_description": "RD",
                "exit_criteria": "E",
                "sequences": ["seq1"],
            }
        ],
        "sequences": [
            {
                "id": "seq1",
                "name": "S",
                "sequence_type": "Exploration",
                "description": "D",
                "goal": "G",
                "exit_triggers": [],
                "location_name": "L",
                "location_theme": "T",
                "location_description": "LD",
                "danger_min": 1,
                "danger_max": 5,
                "npcs": [
                    {
                        "scenario_npc_id": "npc1",
                        "name": "N",
                        "description": "D",
                        "tags": [],
                        "state": {"numeric": {"HP": 50}},
                    }
                ],
                "enemies": [],
                "items": [
                    {
                        "item_id": 1,
                        "name": "I",
                        "description": "D",
                        "item_type": "misc",
                        "meta": {},
                    }
                ],
            }
        ],
        "relations": [],
    }

    scenario_id = await adapter.save_scenario(concept, data)
    assert scenario_id is not None

    # Disk I/O Monitoring After
    io_after = psutil.disk_io_counters()
    proc_io_after = proc.io_counters().write_bytes

    global_write_diff = io_after.write_bytes - io_before.write_bytes
    proc_write_diff = proc_io_after - proc_io_before

    logger.info(f"📊 [Disk IO] Global Write: {global_write_diff / 1024:.2f} KB")
    logger.info(f"📊 [Disk IO] Process Write: {proc_write_diff / 1024:.2f} KB")

    # Assert reasonable disk usage (e.g., less than 1MB for a single scenario save)
    # Note: Global might be higher due to other system activities,
    # but process should be low.
    assert proc_write_diff < 1024 * 1024, (
        f"Suspiciously high disk write: {proc_write_diff} bytes"
    )

    graph = await adapter.get_scenario_full_graph(scenario_id)

    assert graph["scenario_id"] == str(scenario_id)

    # Acts now contain IDs (strings), not sequence objects
    sequences_ids = graph["acts"][0]["sequences"]
    assert "seq1" in sequences_ids
    assert isinstance(sequences_ids[0], str)
