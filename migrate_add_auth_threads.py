"""Migration script to add authentication and thread support.

Run this script to upgrade your database schema:
    python migrate_add_auth_threads.py
"""

import sys
import os

# Add parent directory to path to import corefoundry modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from corefoundry.app.db.connection import engine, init_db
from corefoundry.app.db.models import Base, Agent, Message, Memory, KnowledgeChunk, ChatUser, Thread
from corefoundry.app.db.auth_models import AuthUser


def run_migration():
    """Run database migration."""
    print("🔄 Running database migration...")
    
    with engine.begin() as conn:
        # Check if auth_users table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'auth_users'
            );
        """))
        auth_users_exists = result.scalar()
        
        if not auth_users_exists:
            print("✅ Creating auth_users table...")
            AuthUser.__table__.create(engine, checkfirst=True)
        else:
            print("⏭️  auth_users table already exists")
        
        # Check if chat_users table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chat_users'
            );
        """))
        chat_users_exists = result.scalar()
        
        if not chat_users_exists:
            print("✅ Creating chat_users table...")
            ChatUser.__table__.create(engine, checkfirst=True)
        else:
            print("⏭️  chat_users table already exists")
        
        # Always ensure default chat user exists (even if table already existed)
        conn.execute(text("""
            INSERT INTO chat_users (name, created_at, updated_at)
            VALUES ('Default User', NOW(), NOW())
            ON CONFLICT (name) DO NOTHING;
        """))
        
        # Verify default user was created/exists
        result = conn.execute(text("SELECT COUNT(*) FROM chat_users;"))
        user_count = result.scalar()
        if user_count == 0:
            raise Exception("Failed to create default chat user")
        print(f"✅ Chat users in database: {user_count}")
        
        # Check if threads table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'threads'
            );
        """))
        threads_exists = result.scalar()
        
        if not threads_exists:
            print("✅ Creating threads table...")
            Thread.__table__.create(engine, checkfirst=True)
        else:
            print("⏭️  threads table already exists")
        
        # Check if messages.thread_id column exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name = 'messages' 
                AND column_name = 'thread_id'
            );
        """))
        thread_id_exists = result.scalar()
        
        if not thread_id_exists:
            print("✅ Adding thread_id column to messages table...")
            conn.execute(text("""
                ALTER TABLE messages 
                ADD COLUMN thread_id INTEGER REFERENCES threads(id) ON DELETE CASCADE;
            """))
            conn.execute(text("""
                CREATE INDEX ix_messages_thread_id ON messages(thread_id);
            """))
        else:
            print("⏭️  messages.thread_id column already exists")
        
        # Backfill: create threads for existing messages (if any)
        result = conn.execute(text("""
            SELECT COUNT(*) FROM messages WHERE thread_id IS NULL;
        """))
        orphan_messages = result.scalar()
        
        if orphan_messages > 0:
            print(f"⚠️  Found {orphan_messages} messages without threads")
            print("✅ Creating default threads for existing messages...")
            
            # Get default user (must exist at this point)
            result = conn.execute(text("""
                SELECT id FROM chat_users ORDER BY id LIMIT 1;
            """))
            default_user_id = result.scalar()
            
            if default_user_id is None:
                raise Exception("No chat_users found in database. Cannot create threads for orphan messages.")
            
            print(f"   Using default chat_user_id: {default_user_id}")
            
            # For each agent with orphan messages, create a thread
            result = conn.execute(text("""
                SELECT DISTINCT agent_id FROM messages WHERE thread_id IS NULL;
            """))
            agent_ids = [row[0] for row in result]
            
            for agent_id in agent_ids:
                # Create a thread for this agent and get the ID directly
                result = conn.execute(text("""
                    INSERT INTO threads (agent_id, user_id, title, created_at, updated_at)
                    VALUES (:agent_id, :user_id, 'Legacy Thread', NOW(), NOW())
                    RETURNING id;
                """), {"agent_id": agent_id, "user_id": default_user_id})
                
                thread_id = result.scalar()
                
                if thread_id is None:
                    raise Exception(f"Failed to create thread for agent_id {agent_id}")
                
                # Assign all orphan messages from this agent to this thread
                update_result = conn.execute(text("""
                    UPDATE messages 
                    SET thread_id = :thread_id 
                    WHERE agent_id = :agent_id AND thread_id IS NULL;
                """), {"thread_id": thread_id, "agent_id": agent_id})
                
                print(f"   ✓ Created thread {thread_id} for agent {agent_id}, migrated {update_result.rowcount} messages")
            
            print(f"✅ Migrated {orphan_messages} messages to default threads")
        else:
            print("✅ No orphan messages to migrate")
    
    print("\n🎉 Migration completed successfully!")
    print("\nNext steps:")
    print("1. Install new dependencies: pip install passlib[bcrypt] pyjwt")
    print("2. Add SECRET_KEY to your .env file")
    print("3. Restart your backend server")
    print("4. Navigate to http://localhost:8000/api/docs to see new auth endpoints")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
