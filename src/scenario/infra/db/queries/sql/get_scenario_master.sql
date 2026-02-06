SELECT id, title, concept, state_manager_id
FROM scenarios
WHERE id = $1 OR state_manager_id = $2
ORDER BY updated_at DESC LIMIT 1;
