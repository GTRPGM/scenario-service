-- src/scenario/infra/db/queries/sql/init_db.sql
-- 1. Ensure Extension
CREATE EXTENSION IF NOT EXISTS age CASCADE;

-- 2. Relational Tables
CREATE TABLE
    IF NOT EXISTS scenarios (
        id UUID PRIMARY KEY,
        title TEXT NOT NULL,
        concept TEXT,
        state_manager_id TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

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

CREATE TABLE
    IF NOT EXISTS scenario_generation_runs (
        id UUID PRIMARY KEY,
        concept TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE TABLE
    IF NOT EXISTS scenario_generation_steps (
        id BIGSERIAL PRIMARY KEY,
        run_id UUID NOT NULL REFERENCES scenario_generation_runs (id) ON DELETE CASCADE,
        checkpoint_id TEXT NOT NULL UNIQUE,
        stage TEXT NOT NULL,
        status TEXT NOT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 1,
        resolved_input JSONB NOT NULL DEFAULT '{}'::jsonb,
        result JSONB,
        error TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_generation_steps_run_stage ON scenario_generation_steps (run_id, stage);

CREATE TABLE
    IF NOT EXISTS scenario_generation_request_logs (
        id UUID PRIMARY KEY,
        run_id UUID REFERENCES scenario_generation_runs (id) ON DELETE SET NULL,
        stage TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        response_payload JSONB,
        status TEXT NOT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        error TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

CREATE INDEX IF NOT EXISTS idx_generation_logs_run_stage ON scenario_generation_request_logs (run_id, stage, created_at DESC);
