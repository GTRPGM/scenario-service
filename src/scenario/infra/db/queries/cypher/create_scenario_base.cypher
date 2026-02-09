SELECT * FROM cypher('scenario_graph'::name, $$
    CREATE (s:Scenario {
        id: $scenario_id,
        title: $title,
        concept: $concept,
        summary: $summary,
        description: $description,
        difficulty: $difficulty,
        genre: $genre,
        tags: $tags,
        total_acts: $total_acts
    })
    RETURN s.id
$$::cstring, $1::agtype) as (id agtype);
