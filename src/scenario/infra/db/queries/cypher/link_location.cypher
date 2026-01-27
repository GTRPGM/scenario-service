-- src/scenario/infra/db/queries/cypher/link_location.cypher

SELECT * FROM cypher('scenario_graph', $$
    MATCH (s:Sequence {id: $seq_id})
    CREATE (l:Location {
        name: $name,
        description: $description
    })
    CREATE (s)-[:LOCATED_AT]->(l)
$$, $1) as (v agtype);
