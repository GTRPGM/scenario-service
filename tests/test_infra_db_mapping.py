import pytest

from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.db.adapter import PostgresScenarioAdapter


@pytest.mark.asyncio
async def test_external_id_mapping_sql_and_graph(real_db_handler):
    """
    State Manager ID 업데이트 시 SQL 테이블과 그래프 DB 모두에
    정상적으로 기록되는지 검증합니다.
    """
    loader = QueryLoader()
    adapter = PostgresScenarioAdapter(real_db_handler, loader)

    # 1. 시나리오 생성
    concept = "Mapping Test"
    data = {"title": "Mapping Title", "acts": [], "sequences": [], "relations": []}
    scenario_id = await adapter.save_scenario(concept, data)

    # 2. 외부 ID 업데이트 (State Manager ID 주입 시뮬레이션)
    external_sm_id = "sm-uuid-12345"
    await adapter.update_external_id(scenario_id, external_sm_id)

    # 3. SQL 레벨 검증
    sql_row = await real_db_handler.fetchrow(
        "SELECT state_manager_id FROM scenarios WHERE id = $1", scenario_id
    )
    assert sql_row["state_manager_id"] == external_sm_id

    # 4. 그래프 레벨 검증
    graph_row = await real_db_handler.fetchrow(
        """
        SELECT * FROM cypher('scenario_graph', $$
            MATCH (s:Scenario {id: $id})
            RETURN s.state_manager_id
        $$, $1) AS (sm_id agtype);
        """,
        json_dumps_val(str(scenario_id)),
    )
    # agtype에서 값을 꺼낼 때는 " " 가 포함될 수 있으므로 정문화 필요
    assert external_sm_id in str(graph_row["sm_id"])


def json_dumps_val(val):
    import json

    return json.dumps({"id": val})
