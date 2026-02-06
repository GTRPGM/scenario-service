SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id}) RETURN s
$$, $1) AS (s agtype);
