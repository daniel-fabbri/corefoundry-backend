# Fix Migration - Quick Guide

## Problema encontrado

A tabela `chat_users` existia mas estava **vazia**, então a migração falhava ao tentar criar threads.

## Solução aplicada

Script atualizado para:
1. ✅ Sempre garantir que existe pelo menos 1 chat_user
2. ✅ Verificar se foi criado corretamente
3. ✅ Melhor tratamento de erros
4. ✅ Melhor logging durante migração

## Como executar (no Ubuntu)

### 1. Verificar estado atual

```bash
# Conectar no PostgreSQL
sudo -u postgres psql -d corefoundry

# Verificar tabelas e contadores
SELECT 'chat_users' as table_name, COUNT(*) FROM chat_users
UNION ALL
SELECT 'threads', COUNT(*) FROM threads
UNION ALL
SELECT 'messages (with thread)', COUNT(*) FROM messages WHERE thread_id IS NOT NULL
UNION ALL
SELECT 'messages (no thread)', COUNT(*) FROM messages WHERE thread_id IS NULL;

# Sair
\q
```

### 2. Rodar migração corrigida

```bash
cd ~/Documents/corefoundry-backend
source .venv/bin/activate
python migrate_add_auth_threads.py
```

### 3. Se ainda der erro, limpar e recomeçar

Se a migração continuar falhando, você pode resetar as tabelas relacionadas:

```bash
# Conectar no PostgreSQL
sudo -u postgres psql -d corefoundry
```

```sql
-- ATENÇÃO: Isso vai apagar threads e desassociar mensagens!
-- Mensagens antigas não serão perdidas, só ficarão sem thread temporariamente

-- Limpar threads existentes
TRUNCATE TABLE threads CASCADE;

-- Limpar chat_users
TRUNCATE TABLE chat_users CASCADE;

-- Remover thread_id das mensagens (elas ficarão órfãs temporariamente)
UPDATE messages SET thread_id = NULL;

-- Sair
\q
```

Depois rode a migração novamente:

```bash
python migrate_add_auth_threads.py
```

### 4. Verificar sucesso

```bash
sudo -u postgres psql -d corefoundry -c "
SELECT 'chat_users' as table_name, COUNT(*) FROM chat_users
UNION ALL
SELECT 'threads', COUNT(*) FROM threads
UNION ALL
SELECT 'messages (with thread)', COUNT(*) FROM messages WHERE thread_id IS NOT NULL;
"
```

Deve mostrar:
- `chat_users`: pelo menos 1
- `threads`: pelo menos 1 (se você tinha mensagens)
- `messages (with thread)`: 135 (todas as suas mensagens antigas)

## Avisos do python-dotenv que aparecem

```
Python-dotenv could not parse statement starting at line 7
Python-dotenv could not parse statement starting at line 8
Python-dotenv could not parse statement starting at line 10
```

**Isso é normal e não afeta!** São apenas avisos sobre comentários no arquivo `.env`.

Para remover esses avisos (opcional), edite seu `.env` no Ubuntu e garanta que comentários ocupem linhas inteiras:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/corefoundry

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Security
SECRET_KEY=your-secret-key-change-this-in-production-use-long-random-string
```

## Próximos passos após migração bem-sucedida

```bash
# Instalar dependências de autenticação
pip install passlib[bcrypt] pyjwt

# Iniciar backend
python -m corefoundry.main
```

Então abra o frontend e registre sua conta!
