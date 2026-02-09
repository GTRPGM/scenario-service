SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario {{id: $scenario_id}})
    SET s.{provider}_id = $external_id
    RETURN s
$$::cstring, $1::agtype) AS (s agtype);
