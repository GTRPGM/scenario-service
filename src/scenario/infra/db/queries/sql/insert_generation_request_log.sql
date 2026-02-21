INSERT INTO scenario_generation_request_logs (
    id,
    run_id,
    stage,
    endpoint,
    request_payload,
    response_payload,
    status,
    retry_count,
    error
)
VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9);
