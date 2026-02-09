SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (scenario:Scenario {id: $scenario_id})-[:HAS_ACT]->()
          -[:HAS_SEQUENCE]->()-[:HAS_ENTITY]->(e1)
    MATCH (e1)-[r:RELATION]->(e2)
    RETURN DISTINCT e1.id as from_id, e2.id as to_id,
           r.type as rel_type, r.affinity as affinity, r.meta as meta
$$::cstring, $1::agtype) AS (from_id agtype, to_id agtype, rel_type agtype,
            affinity agtype, meta agtype);
