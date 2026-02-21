SELECT
    checkpoint_id,
    stage,
    status,
    attempt_count,
    resolved_input,
    result,
    error,
    created_at
FROM scenario_generation_steps
WHERE run_id = $1
ORDER BY created_at ASC;
