-- src/scenario/infra/db/queries/cypher/create_entity.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Sequence {id: $seq_id})
    CREATE (s)-[:HAS_ENTITY]->(e:EntityTemplate {
        id: $ent_id,
        name: $name,
        category: $entity_category,
        description: $description,
        interaction_guide: $interaction_guide,
        disposition: $disposition,
        occupation: $occupation,
        dialogue_style: $dialogue_style,
        item_type: $item_type,
        grade: $grade,
        base_price: $base_price,
        weight: $weight,
        effect_value: $effect_value,
        enemy_type: $enemy_type,
        base_difficulty: $base_difficulty,
        combat_description: $combat_description
    })
$$, $1) as (v agtype);
