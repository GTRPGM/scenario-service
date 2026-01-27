-- src/writer/infra/db/queries/sql/update_session_state.sql

UPDATE session_states
SET
    current_act_id = $1,
    current_sequence_id = $2,
    context_data = $3,
    updated_at = CURRENT_TIMESTAMP
WHERE session_id = $4;
