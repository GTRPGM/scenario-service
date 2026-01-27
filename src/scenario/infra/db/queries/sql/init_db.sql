-- src/scenario/infra/db/queries/sql/init_db.sql
-- 1. Ensure Extension
CREATE EXTENSION IF NOT EXISTS age CASCADE;

-- 2. Relational Tables
CREATE TABLE
    IF NOT EXISTS session_states (
        session_id UUID PRIMARY KEY,
        scenario_id UUID NOT NULL,
        current_act_id TEXT NOT NULL,
        current_sequence_id TEXT NOT NULL,
        context_data JSONB NOT NULL DEFAULT '{}',
        updated_at TIMESTAMP
        WITH
            TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
