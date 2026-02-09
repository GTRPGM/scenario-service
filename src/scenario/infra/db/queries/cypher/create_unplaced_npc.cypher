SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})
    CREATE (s)-[:HAS_UNPLACED_ENTITY]->(e:EntityTemplate {
        id: $ent_id,
        master_id: $master_id,
        name: $name,
        category: 'NPC',
        description: $description,
        tags: $tags,
        state: $state,
        meta: {},
        dropped_items: []
    })
$$::cstring, $1::agtype) as (v agtype);
