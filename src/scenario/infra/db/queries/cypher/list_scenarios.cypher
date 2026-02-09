-- src/scenario/infra/db/queries/cypher/list_scenarios.cypher

SELECT * FROM cypher('scenario_graph'::name, $$
    MATCH (s:Scenario)
    RETURN s.id as id, s.concept as concept, s.summary as summary
$$::cstring) as (id agtype, concept agtype, summary agtype);
