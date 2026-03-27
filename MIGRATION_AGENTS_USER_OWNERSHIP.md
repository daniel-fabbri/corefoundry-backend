# Migration: Add User Ownership to Agents

## Overview

This migration adds user ownership to agents, ensuring each user can only see and manage their own agents.

## What Changed

1. **Database Schema**:
   - Added `user_id` column to the `agents` table
   - Foreign key constraint to `auth_users` table
   - Index on `user_id` for better query performance

2. **API Changes**:
   - All agent endpoints now require authentication
   - Agents are automatically scoped to the authenticated user
   - User can only access their own agents

3. **Frontend Changes**:
   - Agent list shows only user's own agents
   - Agent count reflects only user's agents
   - Agent selection in dropdowns filtered by user

## Migration Instructions

### Prerequisites

- Ensure at least one user exists in the `auth_users` table
- Backup your database before running the migration

### Running the Migration

#### Option 1: Using Python Script (Recommended)

```bash
cd corefoundry-backend
python migrate_agents_add_user_id.py
```

This script will:
- Add the `user_id` column to the `agents` table
- Assign all existing agents to the first user
- Add foreign key constraints and indexes
- Provide verification output

#### Option 2: Using SQL Script

If you prefer to run the SQL directly:

```bash
psql -U your_username -d corefoundry -f migrate_agents_to_auth_users.sql
```

Or using pgAdmin or your preferred PostgreSQL client:
1. Open `migrate_agents_to_auth_users.sql`
2. Execute the SQL statements

### Verification

After running the migration, verify the changes:

```sql
-- Check the schema
\d agents

-- Check agent ownership distribution
SELECT 
    user_id, 
    u.username, 
    COUNT(*) as agent_count 
FROM agents a
LEFT JOIN auth_users u ON a.user_id = u.id
GROUP BY user_id, u.username;
```

## Post-Migration

### Existing Data

- All existing agents will be assigned to the first user in the system
- If you need to reassign agents to different users, you can do so manually:

```sql
-- Reassign specific agents to another user
UPDATE agents 
SET user_id = <target_user_id> 
WHERE id IN (<agent_id_1>, <agent_id_2>, ...);
```

### API Behavior

After migration, all agent-related API endpoints require authentication:

- `GET /api/agents/` - Returns only the authenticated user's agents
- `POST /api/agents/create` - Creates an agent owned by the authenticated user
- `GET /api/agents/{id}` - Returns agent only if owned by authenticated user
- `DELETE /api/agents/{id}` - Deletes agent only if owned by authenticated user
- Similar restrictions apply to chat, threads, and history endpoints

### Error Handling

If you encounter errors:

1. **No users in auth_users table**:
   ```
   SOLUTION: Create at least one user through the registration endpoint first
   ```

2. **Column already exists**:
   ```
   SOLUTION: Migration was already run, or partial migration exists. 
   Check current schema and adjust migration accordingly.
   ```

3. **Foreign key violation**:
   ```
   SOLUTION: Ensure all user_id values in agents table reference valid auth_users.id
   ```

## Rollback

If you need to rollback this migration:

```sql
-- Remove foreign key constraint
ALTER TABLE agents DROP CONSTRAINT IF EXISTS fk_agents_user_id;

-- Remove index
DROP INDEX IF EXISTS idx_agents_user_id;

-- Remove column
ALTER TABLE agents DROP COLUMN IF EXISTS user_id;
```

**Warning**: Rolling back will remove the user ownership feature and all agents will be visible to all users again.

## Testing

After migration:

1. Create a new user account
2. Login with the new user
3. Create a new agent
4. Logout and login with a different user
5. Verify that the first user's agent is NOT visible

## Support

If you encounter any issues during migration, please check:
- Database connection settings in `corefoundry/configs/settings.py`
- PostgreSQL logs for detailed error messages
- Existing database constraints that might conflict

## Summary

This migration enhances security and data isolation by ensuring each user has their own private workspace with isolated agents, conversations, and data.
