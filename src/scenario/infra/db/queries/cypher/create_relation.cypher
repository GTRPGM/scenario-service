-- src/scenario/infra/db/queries/cypher/create_relation.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Scenario {id: $scenario_id})-[:HAS_ACT]->()-[:HAS_SEQUENCE]->()-[:HAS_ENTITY]->(a:EntityTemplate {id: $from_id})
    MATCH (s)-[:HAS_ACT]->()-[:HAS_SEQUENCE]->()-[:HAS_ENTITY]->(b:EntityTemplate {id: $to_id})
    CREATE (a)-[:RELATION {
        type: $relation_type,
        affinity: $affinity,
        meta: $meta
    }]->(b)
$$, $1) as (v agtype);
