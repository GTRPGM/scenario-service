SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->(a:Act)
    RETURN a.id as id, a
$$, $1) AS (id agtype, a agtype);
