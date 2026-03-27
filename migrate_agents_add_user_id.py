#!/usr/bin/env python3
"""Migration script to add user_id to agents table."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from corefoundry.configs.settings import settings

def run_migration():
    """Run the migration to add user_id to agents table."""
    
    print("CoreFoundry Database Migration")
    print("=" * 50)
    print("Migration: Add user_id to agents table")
    print("=" * 50)
    print()
    
    # Create database connection
    print(f"Connecting to database: {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    
    migration_sql = """
    -- Migration to add user_id to agents table
    
    -- Step 1: Add user_id column (nullable first)
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'agents' AND column_name = 'user_id'
        ) THEN
            ALTER TABLE agents ADD COLUMN user_id INTEGER;
            RAISE NOTICE 'Added user_id column to agents table';
        ELSE
            RAISE NOTICE 'user_id column already exists';
        END IF;
    END $$;
    
    -- Step 2: Assign all existing agents to the first user
    DO $$
    DECLARE
        first_user_id INTEGER;
        agents_updated INTEGER;
    BEGIN
        -- Get the first user ID
        SELECT id INTO first_user_id FROM auth_users ORDER BY id LIMIT 1;
        
        IF first_user_id IS NULL THEN
            RAISE EXCEPTION 'No users found in auth_users table. Please create at least one user first.';
        END IF;
        
        -- Update agents without user_id
        UPDATE agents 
        SET user_id = first_user_id
        WHERE user_id IS NULL;
        
        GET DIAGNOSTICS agents_updated = ROW_COUNT;
        RAISE NOTICE 'Assigned % agents to user ID %', agents_updated, first_user_id;
    END $$;
    
    -- Step 3: Make user_id NOT NULL
    DO $$
    BEGIN
        ALTER TABLE agents ALTER COLUMN user_id SET NOT NULL;
        RAISE NOTICE 'Set user_id column to NOT NULL';
    END $$;
    
    -- Step 4: Add foreign key constraint if it doesn't exist
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'fk_agents_user_id'
        ) THEN
            ALTER TABLE agents 
            ADD CONSTRAINT fk_agents_user_id 
            FOREIGN KEY (user_id) REFERENCES auth_users(id);
            RAISE NOTICE 'Added foreign key constraint fk_agents_user_id';
        ELSE
            RAISE NOTICE 'Foreign key constraint already exists';
        END IF;
    END $$;
    
    -- Step 5: Add index for better query performance
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE indexname = 'idx_agents_user_id'
        ) THEN
            CREATE INDEX idx_agents_user_id ON agents(user_id);
            RAISE NOTICE 'Added index idx_agents_user_id';
        ELSE
            RAISE NOTICE 'Index already exists';
        END IF;
    END $$;
    """
    
    try:
        with engine.begin() as conn:
            print("Running migration...")
            print()
            
            # Execute migration
            result = conn.execute(text(migration_sql))
            
            print("\n✅ Migration completed successfully!")
            print()
            
            # Show stats
            print("Verification:")
            stats = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_agents, 
                    user_id,
                    u.username
                FROM agents a
                LEFT JOIN auth_users u ON a.user_id = u.id
                GROUP BY user_id, u.username
                ORDER BY user_id
            """))
            
            print()
            print("Agents per user:")
            for row in stats:
                print(f"  User {row.user_id} ({row.username}): {row.total_agents} agents")
            
            print()
            print("=" * 50)
            print("Migration completed! You can now restart your application.")
            print("=" * 50)
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check the error message above and fix any issues.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        run_migration()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
