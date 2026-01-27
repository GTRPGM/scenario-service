-- src/scenario/infra/db/queries/cypher/create_scenario_base.cypher

SELECT * FROM cypher('scenario_graph', $$
    CREATE (s:Scenario {id: $scenario_id, concept: $concept, summary: $summary})
$$, $1) as (v agtype);
