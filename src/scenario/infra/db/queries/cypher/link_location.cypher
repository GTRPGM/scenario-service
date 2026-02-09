-- src/scenario/infra/db/queries/cypher/link_location.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->()-[:HAS_SEQUENCE]->(seq_node:Sequence {id: $seq_id})

    CREATE (seq_node)-[:LOCATED_AT]->(loc_node:Location {
        id: $location_master_id,
        name: $location_name,
        theme: $location_theme,
        description: $location_description,
        danger_min: $danger_min,
        danger_max: $danger_max
    })
$$::cstring, $1::agtype) as (v agtype);
