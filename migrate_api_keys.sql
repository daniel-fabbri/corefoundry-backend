-- Migration: Add API Keys table
-- Date: 2026-03-27
-- Description: Create api_keys table for user API authentication

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    prefix VARCHAR(20) NOT NULL,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON api_keys TO corefoundry_user;
GRANT USAGE, SELECT ON SEQUENCE api_keys_id_seq TO corefoundry_user;

-- Verify table creation
SELECT 'api_keys table created successfully' AS status;
