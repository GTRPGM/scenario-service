SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->(a:Act)
          -[:HAS_SEQUENCE]->(seq:Sequence)
    OPTIONAL MATCH (seq)-[:LOCATED_AT]->(loc:Location)
    RETURN a.id as act_id, seq.id as seq_id, seq, loc
$$, $1) AS (act_id agtype, seq_id agtype, seq agtype, loc agtype);
