SELECT id, concept, created_at
FROM scenario_generation_runs
WHERE id = $1;
