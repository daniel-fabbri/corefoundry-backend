# Migration Instructions: Threads to Auth Users

## O que foi alterado

Esta migração remove o campo de seleção de usuário da página de chat e usa automaticamente o usuário autenticado. Também atualiza o backend para que as threads referenciem `auth_users` ao invés de `chat_users`.

### Alterações no Frontend:
- ✅ Removido select de usuário no ChatPage
- ✅ Integrado `useAuth()` para usar o usuário logado automaticamente
- ✅ Simplificada a interface: apenas Agent + Thread

### Alterações no Backend:
- ✅ Modelo `Thread` agora referencia `auth_users` ao invés de `chat_users`
- ✅ `AgentService.create_thread()` valida contra `AuthUser`
- ✅ Script de migração criado: `migrate_threads_to_auth_users.py`

## Passos para rodar no Ubuntu

⚠️ **IMPORTANTE**: Se a migração falhou anteriormente, primeiro execute:
```bash
python fix_threads_fk.py
```

Este script restaura o estado do banco e permite tentar a migração novamente.

### 1. Pull das alterações
```bash
cd /caminho/para/CoreFoundry
git pull
```

### 2. Rodar a migração do banco de dados
```bash
cd corefoundry-backend
python migrate_threads_to_auth_users.py
```

**O que o script faz:**
- Remove a foreign key de `threads.user_id -> chat_users.id`
- Adiciona nova foreign key `threads.user_id -> auth_users.id`
- Remove threads órfãs (se existirem user_ids que não estão em auth_users)
- Valida que a migração foi bem-sucedida

### 3. Reiniciar o backend
```bash
# Se estiver usando docker-compose
docker-compose restart backend

# Ou se estiver rodando manual
pkill -f "python.*main.py"
./run.sh
```

### 4. Rebuild do frontend (se necessário)
```bash
cd ../corefoundry-frontend
npm run build
```

### 5. Testar
1. Faça login na aplicação
2. Vá para a página Chat
3. Selecione um Agent
4. Clique em "New Thread" - não deve mais aparecer erro "User 1 not found"
5. Verifique se consegue criar threads e enviar mensagens

## Rollback (se necessário)

Se algo der errado, você pode reverter:

```bash
# 1. Reverter código
git revert HEAD

# 2. Restaurar foreign key antiga no banco (SQL manual)
psql -U postgres -d corefoundry
```

```sql
ALTER TABLE threads DROP CONSTRAINT threads_user_id_fkey;
ALTER TABLE threads ADD CONSTRAINT threads_user_id_fkey 
  FOREIGN KEY (user_id) REFERENCES chat_users(id) ON DELETE CASCADE;
```

## Notas

- A tabela `chat_users` não é removida nesta migração (para compatibilidade)
- Threads antigas serão preservadas se os user_ids corresponderem a auth_users existentes
- Se threads órfãs forem detectadas, o script as remove automaticamente
