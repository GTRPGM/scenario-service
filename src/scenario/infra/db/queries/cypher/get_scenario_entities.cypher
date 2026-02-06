SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})
    OPTIONAL MATCH (s)-[:HAS_ACT]->()-[:HAS_SEQUENCE]->(seq:Sequence)-[:HAS_ENTITY]->(e:EntityTemplate)
    OPTIONAL MATCH (s)-[:HAS_UNPLACED_ENTITY]->(ue:EntityTemplate)
    RETURN seq.id as seq_id, e.id as ent_id, e, ue.id as uent_id, ue
$$, $1) AS (seq_id agtype, ent_id agtype, e agtype, uent_id agtype, ue agtype);
