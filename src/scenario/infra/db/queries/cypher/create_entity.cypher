-- src/scenario/infra/db/queries/cypher/create_entity.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->()-[:HAS_SEQUENCE]->(seq_node:Sequence {id: $seq_id})
    CREATE (seq_node)-[:HAS_ENTITY]->(entity_node:EntityTemplate {
        id: $ent_id,
        master_id: $master_id,
        name: $name,
        category: $entity_category,
        description: $description,
        tags: $tags,
        state: $state,
        meta: $meta,
        dropped_items: $dropped_items
    })
$$, $1) as (v agtype);
