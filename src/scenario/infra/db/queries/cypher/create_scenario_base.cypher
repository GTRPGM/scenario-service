SELECT * FROM cypher('scenario_graph', $$
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
$$, $1) as (id agtype);
