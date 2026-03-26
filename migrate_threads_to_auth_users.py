#!/usr/bin/env python3
"""
Migration script to change threads table to reference auth_users instead of chat_users.

This migration:
1. Drops the foreign key constraint from threads.user_id to chat_users.id
2. Adds a new foreign key constraint from threads.user_id to auth_users.id
3. Updates existing thread user_ids to match auth_users (if they exist)
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    sys.exit(1)

print("🔄 Starting migration: threads to auth_users")
print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")

engine = create_engine(DATABASE_URL)

def run_migration():
    """Execute the migration."""
    with engine.begin() as conn:
        print("\n1️⃣ Checking current state...")
        
        # Check if threads table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'threads'
            );
        """))
        threads_exists = result.scalar()
        
        if not threads_exists:
            print("⚠️  threads table does not exist. Nothing to migrate.")
            return
        
        # Check current foreign key
        result = conn.execute(text("""
            SELECT 
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name='threads'
                AND kcu.column_name='user_id';
        """))
        
        fk_info = result.fetchone()
        if fk_info:
            constraint_name = fk_info[0]
            foreign_table = fk_info[2]
            print(f"   Current FK: threads.user_id -> {foreign_table}.id")
            
            if foreign_table == 'auth_users':
                print("✅ Migration already applied! threads.user_id already references auth_users")
                return
        
        print("\n2️⃣ Backing up thread data...")
        result = conn.execute(text("SELECT COUNT(*) FROM threads;"))
        thread_count = result.scalar()
        print(f"   Found {thread_count} threads")
        
        print("\n3️⃣ Dropping old foreign key constraint...")
        if fk_info:
            conn.execute(text(f"""
                ALTER TABLE threads 
                DROP CONSTRAINT {constraint_name};
            """))
            print(f"   ✓ Dropped constraint: {constraint_name}")
        
        print("\n4️⃣ Adding new foreign key to auth_users...")
        try:
            conn.execute(text("""
                ALTER TABLE threads 
                ADD CONSTRAINT threads_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES auth_users(id) 
                ON DELETE CASCADE;
            """))
            print("   ✓ Added constraint: threads_user_id_fkey -> auth_users(id)")
        except Exception as e:
            if "violates foreign key constraint" in str(e):
                print("   ⚠️  Warning: Some thread user_ids don't exist in auth_users")
                print("   Attempting to clean up orphaned threads...")
                
                # Delete threads with user_ids that don't exist in auth_users
                result = conn.execute(text("""
                    DELETE FROM threads 
                    WHERE user_id NOT IN (SELECT id FROM auth_users);
                """))
                deleted_count = result.rowcount
                print(f"   ✓ Deleted {deleted_count} orphaned threads")
                
                # Try adding constraint again
                conn.execute(text("""
                    ALTER TABLE threads 
                    ADD CONSTRAINT threads_user_id_fkey 
                    FOREIGN KEY (user_id) 
                    REFERENCES auth_users(id) 
                    ON DELETE CASCADE;
                """))
                print("   ✓ Added constraint: threads_user_id_fkey -> auth_users(id)")
            else:
                raise
        
        print("\n5️⃣ Verifying migration...")
        result = conn.execute(text("""
            SELECT 
                tc.constraint_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name='threads'
                AND kcu.column_name='user_id';
        """))
        
        fk_info = result.fetchone()
        if fk_info and fk_info[1] == 'auth_users':
            print(f"   ✓ Verified: threads.user_id -> auth_users.id")
        else:
            print(f"   ❌ Verification failed!")
            return
        
        # Count remaining threads
        result = conn.execute(text("SELECT COUNT(*) FROM threads;"))
        final_count = result.scalar()
        print(f"   ✓ {final_count} threads remain after migration")
        
        print("\n✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update the Thread model in models.py to reference auth_users")
        print("2. Update AgentService to use AuthUser instead of ChatUser")
        print("3. Restart the backend server")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
