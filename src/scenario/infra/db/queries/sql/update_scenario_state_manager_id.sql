UPDATE scenarios
SET state_manager_id = $1, updated_at = CURRENT_TIMESTAMP
WHERE id = $2;
