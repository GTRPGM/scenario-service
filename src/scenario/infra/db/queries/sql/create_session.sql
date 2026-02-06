-- src/scenario/infra/db/queries/sql/create_session.sql

INSERT INTO session_states (
    session_id,
    scenario_id,
    current_act_id,
    current_sequence_id,
    context_data,
    updated_at
) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
ON CONFLICT (session_id) DO UPDATE SET
    scenario_id = EXCLUDED.scenario_id,
    current_act_id = EXCLUDED.current_act_id,
    current_sequence_id = EXCLUDED.current_sequence_id,
    context_data = EXCLUDED.context_data,
    updated_at = CURRENT_TIMESTAMP;
