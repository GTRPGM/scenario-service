-- src/scenario/infra/db/queries/cypher/create_sequences.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (a:Act {id: $act_id})
    UNWIND $sequences as seq_data
    CREATE (s:Sequence {
        id: seq_data.id,
        name: seq_data.name,
        description: seq_data.description,
        goal: seq_data.goal,
        exit_triggers: seq_data.exit_triggers
    })
    CREATE (l:Location {
        name: seq_data.location_name,
        description: seq_data.location_description
    })
    CREATE (a)-[:HAS_SEQUENCE]->(s)
    CREATE (s)-[:LOCATED_AT]->(l)
$$, $1) as (v agtype);
