-- Migration to add user_id to agents table
-- This script adds user_id FK to agents and assigns all existing agents to the first user
--
-- DATABASE: PostgreSQL
-- NOTE: This SQL is written for PostgreSQL syntax
--       If VS Code shows errors, ignore them - they are validation errors for SQL Server
--       The syntax is correct for PostgreSQL
--
-- USAGE:
--   psql -U your_username -d corefoundry -f migrate_agents_to_auth_users.sql
--   OR use pgAdmin or your preferred PostgreSQL client

-- Add user_id column (nullable first)
-- Note: COLUMN keyword is PostgreSQL syntax (VS Code may show false error if SQL Server dialect is set)
-- @formatter:off
ALTER TABLE agents ADD COLUMN user_id INTEGER;
-- @formatter:on

-- Assign all existing agents to the first user
-- If no users exist, you'll need to create one first
UPDATE agents 
SET user_id = (SELECT id FROM auth_users ORDER BY id LIMIT 1)
WHERE user_id IS NULL;

-- Make user_id NOT NULL
ALTER TABLE agents 
ALTER COLUMN user_id SET NOT NULL;

-- Add foreign key constraint
ALTER TABLE agents 
ADD CONSTRAINT fk_agents_user_id 
FOREIGN KEY (user_id) REFERENCES auth_users(id);

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id);

-- Verify the migration
SELECT 'Migration completed successfully!' as status;
SELECT COUNT(*) as total_agents, user_id FROM agents GROUP BY user_id;
