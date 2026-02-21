SELECT id
FROM scenarios
WHERE concept = $1
ORDER BY updated_at DESC, created_at DESC;
