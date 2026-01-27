-- src/scenario/infra/db/queries/cypher/create_sequence.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (a:Act {id: $act_id})
    CREATE (a)-[:HAS_SEQUENCE]->(s:Sequence {
        id: $seq_id,
        name: $name,
        type: $sequence_type,
        description: $description,
        goal: $goal,
        exit_triggers: $exit_triggers
    })-[:LOCATED_AT]->(l:Location {
        name: $location_name,
        theme: $location_theme,
        description: $location_description,
        danger_min: $danger_min,
        danger_max: $danger_max
    })
$$, $1) as (v agtype);
