SELECT
    id,
    stage,
    endpoint,
    request_payload,
    response_payload,
    status,
    retry_count,
    error,
    created_at
FROM scenario_generation_request_logs
WHERE run_id = $1
ORDER BY created_at ASC;
