-- Migration: Add agent_id column to knowledge_chunks table
-- This allows knowledge to be scoped per agent

-- Add agent_id column (nullable for backward compatibility)
ALTER TABLE knowledge_chunks 
ADD COLUMN IF NOT EXISTS agent_id INTEGER;

-- Add foreign key constraint
ALTER TABLE knowledge_chunks 
ADD CONSTRAINT fk_knowledge_chunks_agent_id 
FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_agent_id 
ON knowledge_chunks(agent_id);

-- Display status
SELECT 'Migration completed successfully: Added agent_id to knowledge_chunks' AS status;
