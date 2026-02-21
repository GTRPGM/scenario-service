SELECT COUNT(*)::int AS cnt
FROM scenario_generation_request_logs
WHERE run_id = $1
  AND stage = $2;
