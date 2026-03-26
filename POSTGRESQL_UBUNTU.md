# PostgreSQL no Ubuntu - Guia Rápido

## Como acessar PostgreSQL no Ubuntu

### 1. Via terminal (psql)

```bash
# Conectar como usuário postgres
sudo -u postgres psql

# Ou conectar diretamente em um banco específico
sudo -u postgres psql -d corefoundry

# Ou com seu usuário (se tiver permissão)
psql -U postgres -d corefoundry
# Senha: postgres (se for a configuração padrão)
```

### 2. Comandos úteis dentro do psql

```sql
-- Listar todos os bancos de dados
\l

-- Conectar em um banco específico
\c corefoundry

-- Listar todas as tabelas
\dt

-- Ver estrutura de uma tabela
\d messages

-- Executar um arquivo SQL
\i /caminho/para/migration.sql

-- Sair do psql
\q
```

## ❌ Você NÃO precisa fazer nada disso manualmente!

O script Python **`migrate_add_auth_threads.py`** já faz tudo automaticamente:

```bash
# No backend (Ubuntu), com venv ativo:
cd corefoundry-backend
python migrate_add_auth_threads.py
```

### O que o script Python faz?

1. ✅ Lê a `DATABASE_URL` do seu `.env`
2. ✅ Conecta no PostgreSQL automaticamente
3. ✅ Verifica quais tabelas existem
4. ✅ Cria as tabelas que faltam (`auth_users`, `chat_users`, `threads`)
5. ✅ Adiciona colunas que faltam (`messages.thread_id`)
6. ✅ Migra dados existentes (mensagens antigas vão para threads default)
7. ✅ Cria índices para performance
8. ✅ Mostra relatório de sucesso

**SQLAlchemy faz toda a execução SQL por você!**

## Quando usar SQL manual?

Use o arquivo `migration.sql` apenas se:
- ❌ O script Python der erro
- ❌ Você quiser entender o que está acontecendo
- ❌ Precisar fazer troubleshooting
- ❌ Quiser ver o schema das tabelas

### Para executar SQL manualmente:

```bash
# Opção 1: Via psql interativo
sudo -u postgres psql -d corefoundry
# Depois copiar e colar os comandos SQL

# Opção 2: Via arquivo
sudo -u postgres psql -d corefoundry -f migration.sql
```

## Verificar se funcionou

```bash
# Conectar no PostgreSQL
sudo -u postgres psql -d corefoundry

# Listar tabelas
\dt

# Deve aparecer:
# - agents
# - messages
# - memory
# - knowledge_chunks
# - auth_users          ← NOVA
# - chat_users          ← NOVA
# - threads             ← NOVA
# - langchain_chat_histories (criada pelo LangChain)
```

## Testar conexão Python → PostgreSQL

```python
# Abra um Python shell no backend
python

# Execute:
from corefoundry.app.db.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.scalar())
    # Deve mostrar a versão do PostgreSQL
```

## 🎯 Resumo

**USE ESTA ORDEM:**

1. ✅ Certifique-se que PostgreSQL está rodando
   ```bash
   sudo systemctl status postgresql
   ```

2. ✅ Confirme que `.env` está correto
   ```env
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/corefoundry
   ```

3. ✅ Rode o script Python (FAZ TUDO PRA VOCÊ!)
   ```bash
   python migrate_add_auth_threads.py
   ```

4. ✅ Inicie o backend
   ```bash
   python -m corefoundry.main
   ```

**Só use SQL manual se o script Python falhar!**
