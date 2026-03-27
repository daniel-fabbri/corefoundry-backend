-- ============================================================
-- Script de Verificação e Migração: Agents User Ownership
-- Execute este arquivo no PostgreSQL do Ubuntu
-- ============================================================
-- 
-- COMO EXECUTAR:
--   sudo -u postgres psql -d corefoundry -f check_and_migrate_agents.sql
--
-- OU dentro do psql:
--   sudo -u postgres psql -d corefoundry
--   \i /caminho/para/check_and_migrate_agents.sql
-- ============================================================

-- Passo 1: Verificar se a coluna user_id já existe
DO $$
DECLARE
    column_exists BOOLEAN;
    user_count INTEGER;
    agent_count INTEGER;
BEGIN
    -- Verificar se a coluna existe
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'agents' AND column_name = 'user_id'
    ) INTO column_exists;
    
    IF column_exists THEN
        RAISE NOTICE '✅ Coluna user_id JÁ EXISTE na tabela agents';
        
        -- Mostrar estatísticas
        SELECT COUNT(*) INTO agent_count FROM agents;
        SELECT COUNT(DISTINCT user_id) INTO user_count FROM agents WHERE user_id IS NOT NULL;
        
        RAISE NOTICE 'Total de agentes: %', agent_count;
        RAISE NOTICE 'Agentes com user_id: %', user_count;
        
        -- Mostrar distribuição
        RAISE NOTICE '--- Distribuição de agentes por usuário ---';
    ELSE
        RAISE NOTICE '❌ Coluna user_id NÃO EXISTE na tabela agents';
        RAISE NOTICE 'Iniciando migração...';
        
        -- Verificar se existem usuários
        SELECT COUNT(*) INTO user_count FROM auth_users;
        IF user_count = 0 THEN
            RAISE EXCEPTION 'ERRO: Não existem usuários na tabela auth_users. Crie pelo menos um usuário primeiro!';
        END IF;
        
        RAISE NOTICE 'Encontrados % usuários em auth_users', user_count;
        
        -- Adicionar a coluna
        ALTER TABLE agents ADD COLUMN user_id INTEGER;
        RAISE NOTICE '✅ Coluna user_id criada';
        
        -- Atribuir todos os agentes ao primeiro usuário
        UPDATE agents 
        SET user_id = (SELECT id FROM auth_users ORDER BY id LIMIT 1)
        WHERE user_id IS NULL;
        
        SELECT COUNT(*) INTO agent_count FROM agents;
        RAISE NOTICE '✅ Atribuídos % agentes ao primeiro usuário', agent_count;
        
        -- Tornar NOT NULL
        ALTER TABLE agents ALTER COLUMN user_id SET NOT NULL;
        RAISE NOTICE '✅ Coluna user_id definida como NOT NULL';
        
        -- Adicionar FK constraint
        ALTER TABLE agents 
        ADD CONSTRAINT fk_agents_user_id 
        FOREIGN KEY (user_id) REFERENCES auth_users(id);
        RAISE NOTICE '✅ Foreign key constraint criada';
        
        -- Adicionar índice
        CREATE INDEX idx_agents_user_id ON agents(user_id);
        RAISE NOTICE '✅ Índice criado';
        
        RAISE NOTICE '🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO!';
    END IF;
END $$;

-- Mostrar distribuição de agentes por usuário
SELECT 
    a.user_id,
    u.username,
    u.email,
    COUNT(a.id) as total_agents,
    MIN(a.created_at) as primeiro_agente,
    MAX(a.created_at) as ultimo_agente
FROM agents a
LEFT JOIN auth_users u ON a.user_id = u.id
GROUP BY a.user_id, u.username, u.email
ORDER BY a.user_id;

-- Verificar schema da tabela agents
\d agents
