SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->(a:Act)
    RETURN a.id as id, a
$$::cstring, $1::agtype) AS (id agtype, a agtype);
