-- src/scenario/infra/db/queries/cypher/create_act.cypher
SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    CREATE (s)-[:HAS_ACT]->(a:Act {
        id: $act_id,
        name: $name,
        region_name: $region_name,
        region_description: $region_description,
        goal: $goal,
        exit_criteria: $exit_criteria
    })
$$, $1) as (v agtype);
