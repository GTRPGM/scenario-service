SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})
    CREATE (s)-[:HAS_UNPLACED_ENTITY]->(e:EntityTemplate {
        id: $ent_id,
        master_id: $master_id,
        name: $name,
        category: 'ITEM',
        description: $description,
        tags: [],
        state: {},
        meta: $meta,
        dropped_items: []
    })
$$::cstring, $1::agtype) as (v agtype);
