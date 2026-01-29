SELECT * FROM cypher('scenario_graph', '
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
', $1) as (v agtype);
