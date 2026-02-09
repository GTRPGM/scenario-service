-- src/scenario/infra/db/queries/cypher/create_sequences.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->(act_node:Act {id: $act_id})
    UNWIND $sequences as seq_item
    CREATE (seq_node:Sequence {
        id: seq_item.id,
        name: seq_item.name,
        description: seq_item.description,
        goal: seq_item.goal,
        exit_triggers: seq_item.exit_triggers
    })
    CREATE (loc_node:Location {
        name: seq_item.location_name,
        description: seq_item.location_description
    })
    CREATE (act_node)-[:HAS_SEQUENCE]->(seq_node)
    CREATE (seq_node)-[:LOCATED_AT]->(loc_node)
$$::cstring, $1::agtype) as (v agtype);
