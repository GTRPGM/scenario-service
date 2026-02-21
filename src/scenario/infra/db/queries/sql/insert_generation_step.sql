INSERT INTO scenario_generation_steps (
    run_id,
    checkpoint_id,
    stage,
    status,
    attempt_count,
    resolved_input,
    result,
    error
)
VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8)
ON CONFLICT (checkpoint_id) DO UPDATE SET
    status = EXCLUDED.status,
    attempt_count = EXCLUDED.attempt_count,
    resolved_input = EXCLUDED.resolved_input,
    result = EXCLUDED.result,
    error = EXCLUDED.error;
