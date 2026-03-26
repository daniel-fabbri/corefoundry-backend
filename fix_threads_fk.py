#!/usr/bin/env python3
"""
Script to fix threads table after failed migration.
This will restore the foreign key to chat_users so we can try the migration again.
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

print("🔧 Fixing threads table foreign key")
print(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'}")

engine = create_engine(DATABASE_URL)

def fix_fk():
    """Fix the foreign key constraint."""
    with engine.begin() as conn:
        print("\n1️⃣ Checking current foreign key state...")
        
        # Check if threads_user_id_fkey exists
        result = conn.execute(text("""
            SELECT constraint_name, 
                   (SELECT table_name FROM information_schema.constraint_column_usage 
                    WHERE constraint_name = tc.constraint_name LIMIT 1) as ref_table
            FROM information_schema.table_constraints AS tc 
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name='threads'
                AND tc.constraint_name = 'threads_user_id_fkey';
        """))
        
        fk_info = result.fetchone()
        if fk_info:
            print(f"   Current FK found: {fk_info[0]} -> {fk_info[1]}")
        else:
            print("   No foreign key constraint found on threads.user_id")
        
        print("\n2️⃣ Dropping any existing foreign key...")
        try:
            conn.execute(text("""
                ALTER TABLE threads 
                DROP CONSTRAINT IF EXISTS threads_user_id_fkey;
            """))
            print("   ✓ Dropped threads_user_id_fkey (if it existed)")
        except Exception as e:
            print(f"   Note: {e}")
        
        print("\n3️⃣ Restoring foreign key to chat_users...")
        try:
            conn.execute(text("""
                ALTER TABLE threads 
                ADD CONSTRAINT threads_user_id_fkey 
                FOREIGN KEY (user_id) 
                REFERENCES chat_users(id) 
                ON DELETE CASCADE;
            """))
            print("   ✓ Restored FK: threads.user_id -> chat_users.id")
        except Exception as e:
            if "already exists" in str(e):
                print("   ℹ️  Foreign key already restored")
            else:
                print(f"   ⚠️  Error: {e}")
                print("   This might be OK if you need to clean up data first")
        
        print("\n4️⃣ Verifying state...")
        result = conn.execute(text("""
            SELECT COUNT(*) FROM threads;
        """))
        thread_count = result.scalar()
        print(f"   Threads in database: {thread_count}")
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM chat_users;
        """))
        chat_user_count = result.scalar()
        print(f"   Chat users in database: {chat_user_count}")
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM auth_users;
        """))
        auth_user_count = result.scalar()
        print(f"   Auth users in database: {auth_user_count}")
        
        print("\n✅ Database state restored!")
        print("\nNext steps:")
        print("1. Run migrate_threads_to_auth_users.py again")

if __name__ == "__main__":
    try:
        fix_fk()
    except Exception as e:
        print(f"\n❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
