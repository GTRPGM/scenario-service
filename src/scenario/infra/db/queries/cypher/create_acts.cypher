-- src/scenario/infra/db/queries/cypher/create_acts.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (scenario_node:Scenario)
    WHERE scenario_node.id = $scenario_id
    UNWIND $acts as act_item
    CREATE (act_node:Act {
        id: act_item.id,
        name: act_item.name,
        goal: act_item.goal,
        description: act_item.description,
        exit_criteria: act_item.exit_criteria
    })
    CREATE (scenario_node)-[:HAS_ACT]->(act_node)
$$::cstring, $1::agtype) as (v agtype);
