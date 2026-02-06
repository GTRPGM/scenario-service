SELECT * FROM cypher('scenario_graph', $$
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
$$, $1) as (v agtype);
