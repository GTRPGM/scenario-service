-- src/scenario/infra/db/queries/cypher/create_sequence.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->(act_node:Act {id: $act_id})

    CREATE (act_node)-[:HAS_SEQUENCE]->(seq_node:Sequence {
        id: $seq_id,
        name: $name,
        sequence_type: $sequence_type,
        description: $description,
        goal: $goal,
        exit_triggers: $exit_triggers
    })
$$::cstring, $1::agtype) as (v agtype);
