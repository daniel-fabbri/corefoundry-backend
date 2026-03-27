-- ============================================
-- Script para Verificar a Tabela AGENTS
-- ============================================

-- 1. Verificar a estrutura da tabela agents
\d agents

-- 2. Ver todos os registros da tabela agents
SELECT 
    id,
    name,
    system_prompt,
    user_id,
    created_at,
    updated_at
FROM agents
ORDER BY created_at DESC;

-- 3. Contar total de agents por usuário
SELECT 
    a.user_id,
    au.username,
    au.full_name,
    COUNT(*) as total_agents
FROM agents a
LEFT JOIN auth_users au ON a.user_id = au.id
GROUP BY a.user_id, au.username, au.full_name
ORDER BY total_agents DESC;

-- 4. Ver agents com informações do usuário proprietário
SELECT 
    a.id,
    a.name,
    a.user_id,
    au.username,
    au.full_name,
    a.created_at
FROM agents a
LEFT JOIN auth_users au ON a.user_id = au.id
ORDER BY a.created_at DESC;

-- 5. Verificar se existem agents sem user_id (NULL)
SELECT COUNT(*) as agents_sem_user
FROM agents
WHERE user_id IS NULL;

-- 6. Estatísticas gerais
SELECT 
    COUNT(*) as total_agents,
    COUNT(DISTINCT user_id) as total_users_with_agents,
    MIN(created_at) as oldest_agent,
    MAX(created_at) as newest_agent
FROM agents;

-- 7. Ver constraints da tabela agents
SELECT
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_name = 'agents'
ORDER BY tc.constraint_type, tc.constraint_name;

-- 8. Ver índices da tabela agents
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'agents';
