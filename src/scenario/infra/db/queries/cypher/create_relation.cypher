-- src/scenario/infra/db/queries/cypher/create_relation.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (a {id: $from_id}), (b {id: $to_id})
    CREATE (a)-[:RELATION {
        type: $relation_type,
        affinity: $affinity,
        meta: $meta
    }]->(b)
$$, $1) as (v agtype);
