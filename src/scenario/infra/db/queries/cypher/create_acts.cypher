-- src/scenario/infra/db/queries/cypher/create_acts.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    UNWIND $acts as act_data
    CREATE (a:Act {id: act_data.id, name: act_data.name, goal: act_data.goal})
    CREATE (s)-[:HAS_ACT]->(a)
$$, $1) as (v agtype);
