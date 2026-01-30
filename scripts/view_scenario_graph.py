# scripts/view_scenario_graph.py

import asyncio
import json
import sys
from collections import defaultdict

from scenario.core.config import settings
from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.query_loader import QueryLoader


async def list_scenarios(db: DatabaseHandler):
    print("\n[*] 저장된 시나리오 목록:")
    query = (
        "SELECT * FROM cypher('scenario_graph', $$ "
        "MATCH (s:Scenario) RETURN s.id, s.concept $$) as (id agtype, concept agtype);"
    )
    rows = await db.fetch(query)
    if not rows:
        print("    (저장된 시나리오가 없습니다)")
        return
    for row in rows:
        print(f"    - ID: {row['id']} | 컨셉: {row['concept']}")


async def view_full_graph(db: DatabaseHandler, scenario_id: str):
    loader = QueryLoader()
    query = loader.load_cypher("get_scenario_full_graph")
    params = json.dumps({"scenario_id": scenario_id})
    rows = await db.fetch(query, params)

    if not rows:
        print(f"[!] ID '{scenario_id}'에 해당하는 시나리오를 찾을 수 없습니다.")
        return

    # Hierarchy: Acts -> Sequences -> Entities
    acts = defaultdict(
        lambda: {
            "name": "",
            "sequences": defaultdict(
                lambda: {"name": "", "location": "", "entities": []}
            ),
        }
    )
    concept = rows[0]["concept"]
    summary = rows[0]["summary"]

    for row in rows:
        a_id = row["act_id"]
        if not a_id:
            continue
        acts[a_id]["name"] = row["act_name"]

        s_id = row["seq_id"]
        if not s_id:
            continue
        acts[a_id]["sequences"][s_id]["name"] = row["seq_name"]
        acts[a_id]["sequences"][s_id]["location"] = (
            f"{row['loc_name']} ({row['loc_theme']})"
        )

        e_id = row["ent_id"]
        if e_id:
            # Gather all non-null attributes
            attrs = {
                "Type": row["ent_cat"],
                "Desc": row["ent_desc"],
                "MasterID": row["ent_master_id"],
                "Tags": row["ent_tags"],
                "State": row["ent_state"],
                "Meta": row["ent_meta"],
                "Drops": row["ent_drops"],
            }
            clean_attrs = {k: v for k, v in attrs.items() if v is not None}
            acts[a_id]["sequences"][s_id]["entities"].append(
                {
                    "name": row["ent_name"],
                    "attrs": clean_attrs,
                }
            )

    print("\n" + "=" * 80)
    print(f"  시나리오: {concept}")
    print(f"  요약: {summary}")
    print("=" * 80)

    for a_id, a_data in acts.items():
        print(f"\n[ACT] {a_data['name']} ({a_id})")
        for _, s_data in a_data["sequences"].items():
            print(f"  └── [SEQ] {s_data['name']} (@ {s_data['location']})")
            for ent in s_data["entities"]:
                attr_str = f"Type: {ent['attrs'].get('Type', 'N/A')}"
                print(f"        ├── [ENT] {ent['name']} | {attr_str}")
                print(f"        │     - 설명: {ent['attrs'].get('Desc', '')[:60]}...")
                if ent["attrs"].get("State"):
                    print(f"        │     - 상태: {ent['attrs'].get('State')}")
    print("\n" + "=" * 80)


async def main():
    db = DatabaseHandler(settings.database_dsn)
    await db.connect()
    try:
        if len(sys.argv) > 1:
            await view_full_graph(db, sys.argv[1])
        else:
            await list_scenarios(db)
            print("\n[사용법] uv run scripts/view_scenario_graph.py <시나리오_ID>")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
