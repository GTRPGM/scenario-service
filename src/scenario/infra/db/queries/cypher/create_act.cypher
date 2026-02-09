-- src/scenario/infra/db/queries/cypher/create_act.cypher
SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (scenario_node:Scenario)
    WHERE scenario_node.id = $scenario_id
    CREATE (scenario_node)-[:HAS_ACT]->(act_node:Act {
        id: $act_id,
        name: $name,
        region_name: $region_name,
        region_description: $region_description,
        goal: $goal,
        exit_criteria: $exit_criteria
    })
$$::cstring, $1::agtype) as (v agtype);
