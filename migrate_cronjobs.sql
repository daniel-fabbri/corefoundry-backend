-- Migration: Add Cronjobs functionality
-- Description: Creates tables for managing scheduled HTTP requests (cronjobs)
-- Date: 2026-04-02

-- Table: cronjobs
-- Stores cronjob configurations
CREATE TABLE IF NOT EXISTS cronjobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    method VARCHAR(10) NOT NULL DEFAULT 'GET',
    headers JSONB,
    body JSONB,
    interval_minutes INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_run_at TIMESTAMP,
    last_status_code INTEGER,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_method CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')),
    CONSTRAINT positive_interval CHECK (interval_minutes > 0)
);

-- Table: cronjob_logs
-- Stores execution history for each cronjob
CREATE TABLE IF NOT EXISTS cronjob_logs (
    id SERIAL PRIMARY KEY,
    cronjob_id INTEGER NOT NULL REFERENCES cronjobs(id) ON DELETE CASCADE,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    response_body TEXT,
    CONSTRAINT positive_response_time CHECK (response_time_ms >= 0)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_cronjobs_user_id ON cronjobs(user_id);
CREATE INDEX IF NOT EXISTS idx_cronjobs_is_active ON cronjobs(is_active);
CREATE INDEX IF NOT EXISTS idx_cronjobs_last_run_at ON cronjobs(last_run_at);
CREATE INDEX IF NOT EXISTS idx_cronjob_logs_cronjob_id ON cronjob_logs(cronjob_id);
CREATE INDEX IF NOT EXISTS idx_cronjob_logs_executed_at ON cronjob_logs(executed_at DESC);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_cronjobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_cronjobs_updated_at
    BEFORE UPDATE ON cronjobs
    FOR EACH ROW
    EXECUTE FUNCTION update_cronjobs_updated_at();

-- Comments for documentation
COMMENT ON TABLE cronjobs IS 'Stores scheduled HTTP request configurations';
COMMENT ON TABLE cronjob_logs IS 'Stores execution history and results of cronjobs';
COMMENT ON COLUMN cronjobs.interval_minutes IS 'How often the cronjob should run (in minutes)';
COMMENT ON COLUMN cronjobs.headers IS 'JSON object with HTTP headers to send with the request';
COMMENT ON COLUMN cronjobs.body IS 'JSON object with request body (for POST/PUT/PATCH methods)';
