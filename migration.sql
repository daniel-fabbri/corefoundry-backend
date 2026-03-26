-- CoreFoundry - Migration SQL
-- Este arquivo mostra o SQL que será executado pelo script Python.
-- VOCÊ NÃO PRECISA EXECUTAR MANUALMENTE - o migrate_add_auth_threads.py faz tudo!
--
-- Se quiser executar manualmente no psql:
--   psql -U postgres -d corefoundry -f migration.sql

-- ==========================
-- 1. Criar tabela auth_users (usuários de autenticação)
-- ==========================
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS ix_auth_users_username ON auth_users(username);

-- ==========================
-- 2. Criar tabela chat_users (contextos de conversa)
-- ==========================
CREATE TABLE IF NOT EXISTS chat_users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_chat_users_name ON chat_users(name);

-- Inserir usuário padrão
INSERT INTO chat_users (name, created_at, updated_at)
VALUES ('Default User', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- ==========================
-- 3. Criar tabela threads (conversas isoladas)
-- ==========================
CREATE TABLE IF NOT EXISTS threads (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES chat_users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Thread',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_threads_agent_id ON threads(agent_id);
CREATE INDEX IF NOT EXISTS ix_threads_user_id ON threads(user_id);

-- ==========================
-- 4. Adicionar coluna thread_id na tabela messages
-- ==========================
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'thread_id'
    ) THEN
        ALTER TABLE messages 
        ADD COLUMN thread_id INTEGER REFERENCES threads(id) ON DELETE CASCADE;
        
        CREATE INDEX ix_messages_thread_id ON messages(thread_id);
    END IF;
END $$;

-- ==========================
-- 5. BACKFILL: Migrar mensagens existentes para threads default
-- ==========================
DO $$ 
DECLARE
    default_user_id INTEGER;
    agent_record RECORD;
    new_thread_id INTEGER;
    orphan_count INTEGER;
BEGIN
    -- Contar mensagens sem thread
    SELECT COUNT(*) INTO orphan_count FROM messages WHERE thread_id IS NULL;
    
    IF orphan_count > 0 THEN
        -- Obter ID do usuário padrão
        SELECT id INTO default_user_id FROM chat_users ORDER BY id LIMIT 1;
        
        -- Para cada agente com mensagens órfãs, criar uma thread
        FOR agent_record IN 
            SELECT DISTINCT agent_id FROM messages WHERE thread_id IS NULL
        LOOP
            -- Criar thread "Legacy Thread" para este agente
            INSERT INTO threads (agent_id, user_id, title, created_at, updated_at)
            VALUES (agent_record.agent_id, default_user_id, 'Legacy Thread', NOW(), NOW())
            RETURNING id INTO new_thread_id;
            
            -- Associar todas as mensagens órfãs deste agente à nova thread
            UPDATE messages 
            SET thread_id = new_thread_id 
            WHERE agent_id = agent_record.agent_id AND thread_id IS NULL;
            
            RAISE NOTICE 'Migrated messages for agent_id % to thread_id %', agent_record.agent_id, new_thread_id;
        END LOOP;
        
        RAISE NOTICE 'Migration complete: % orphan messages migrated', orphan_count;
    ELSE
        RAISE NOTICE 'No orphan messages to migrate';
    END IF;
END $$;

-- ==========================
-- 6. Criar tabela para LangChain history (opcional)
-- ==========================
-- Esta tabela é criada automaticamente pelo PostgresChatMessageHistory do LangChain
-- Aqui está o schema para referência:

CREATE TABLE IF NOT EXISTS langchain_chat_histories (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_langchain_chat_histories_session_id 
ON langchain_chat_histories(session_id);

-- ==========================
-- Verificações
-- ==========================
SELECT 'auth_users' as table_name, COUNT(*) as records FROM auth_users
UNION ALL
SELECT 'chat_users', COUNT(*) FROM chat_users
UNION ALL
SELECT 'threads', COUNT(*) FROM threads
UNION ALL
SELECT 'messages (with thread)', COUNT(*) FROM messages WHERE thread_id IS NOT NULL
UNION ALL
SELECT 'messages (orphan)', COUNT(*) FROM messages WHERE thread_id IS NULL;

-- Fim do script
