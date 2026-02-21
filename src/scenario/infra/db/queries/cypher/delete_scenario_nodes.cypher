SELECT *
FROM cypher('scenario_graph'::name, $$
    MATCH (n)
    WHERE n.id = $scenario_id OR n.scenario_id = $scenario_id
    DETACH DELETE n
    RETURN 1
$$::cstring, $1::agtype) AS (ok agtype);
