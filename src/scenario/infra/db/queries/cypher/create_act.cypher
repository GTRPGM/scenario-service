-- src/scenario/infra/db/queries/cypher/create_act.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    CREATE (s)-[:HAS_ACT]->(a:Act {id: $act_id, name: $name, goal: $goal})
$$, $1) as (v agtype);
