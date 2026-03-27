# 🐛 Debug do Knowledge Base - Guia Completo

## ✅ Bugs Corrigidos

### 1. AttributeError: 'AgentService' object has no attribute 'get_messages'
**Arquivo**: `corefoundry/app/routes/agents.py`
- **Problema**: Endpoint `/api/agents/{id}/history` chamava método inexistente
- **Solução**: Trocado `service.get_messages()` → `service.get_conversation_history()`

### 2. Logs de Debug Implementados
**Arquivos**: 
- `corefoundry/app/services/agent_service.py`
- `corefoundry/app/services/knowledge_service.py`
- `corefoundry/main.py`

Agora o sistema loga:
- `use_knowledge` flag (true/false)
- Quantos chunks foram encontrados
- Preview de cada chunk (source, agent_id, conteúdo)
- Warnings quando nenhum chunk é encontrado
- Total de chunks no banco (para diagnóstico)

## 🚀 Como Testar no Ubuntu

### 1. Pull e Restart
```bash
cd ~/Documents/corefoundry-backend
git pull
source .venv/bin/activate

# Restart backend
pkill -f uvicorn  # ou Ctrl+C se estiver em terminal
uvicorn corefoundry.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Verificar Chunks no Banco
```bash
chmod +x check_knowledge.sh
./check_knowledge.sh
```

Este script mostra:
- Estrutura da tabela
- Total de chunks
- Chunks por agent
- Preview dos últimos 5
- Teste de busca por "barco"

### 3. Fazer Upload de Arquivo de Teste

Crie `teste.txt`:
```txt
O barco era vermelho
A tela era azul
```

Upload via interface:
1. Acesse agent detail page
2. Knowledge Base → Upload File
3. Selecione `teste.txt`
4. Verifique se aparece na lista

### 4. Testar Chat com Knowledge

**IMPORTANTE**: Ative o switch "Use Knowledge Base"

```bash
# Via interface
1. Chat → Selecione agent
2. ATIVE "Use Knowledge Base" 
3. Pergunte: "Qual era a cor do barco?"
4. Observe os logs no terminal do backend
```

## 📋 Logs Esperados

Quando `use_knowledge=true`:

```log
[INFO] corefoundry.agent.chat: === CHAT REQUEST === agent_id=10 user_id=1 thread_id=16 use_knowledge=True
[INFO] corefoundry.agent.chat: Knowledge search: query='Qual era a cor do barco?' agent_id=10
[INFO] corefoundry.knowledge.search: Searching chunks: query='Qual era a cor do barco?' agent_id=10 limit=3
[INFO] corefoundry.knowledge.search: Filtering by agent_id=10
[INFO] corefoundry.knowledge.search: Search returned 1 chunks
[INFO] corefoundry.agent.chat: Found 1 relevant chunks
[INFO] corefoundry.agent.chat: Chunk[0]: id=42 source='teste.txt' agent_id=10 preview='O barco era vermelho\nA tela era azul'
[INFO] corefoundry.agent.chat: Adding context to messages (41 chars total)
```

Se **NENHUM chunk** for encontrado:
```log
[INFO] corefoundry.knowledge.search: Search returned 0 chunks
[WARNING] corefoundry.knowledge.search: No matches found! Total chunks in DB: 5, Chunks for agent_id=10: 2
[WARNING] corefoundry.agent.chat: NO CHUNKS FOUND! Check: 1) chunks exist for agent_id=10, 2) query matches content
[INFO] corefoundry.agent.chat: use_knowledge=False, skipping knowledge search
```

## 🔍 Checklist de Debug

### ❌ Agent não usa knowledge
1. ✅ Switch "Use Knowledge Base" está **ATIVO**?
2. ✅ Logs mostram `use_knowledge=True`?
3. ✅ Logs mostram chunks encontrados?
4. ✅ Chunks têm o `agent_id` correto?

### ❌ Nenhum chunk encontrado
```bash
# Verificar se chunks existem
psql -U corefoundry -d corefoundry -c "SELECT id, agent_id, source, substring(content from 1 for 100) FROM knowledge_chunks WHERE agent_id = 10;"

# Se retornar vazio: upload não funcionou
# Se agent_id é NULL: migração não foi executada
# Se content não contém a palavra: busca é case-sensitive
```

### ❌ Upload não associa agent_id
```bash
# Executar migração
cd ~/Documents/corefoundry-backend
chmod +x migrate_knowledge.sh
./migrate_knowledge.sh

# Verificar coluna existe
psql -U corefoundry -d corefoundry -c "\d knowledge_chunks"
# Deve mostrar: agent_id | integer |  |  |
```

### ❌ Busca não encontra (mas chunks existem)
A busca usa `ILIKE '%query%'`:
- `"barco"` → encontra "O barco era vermelho" ✅
- `"Barco"` → encontra (case-insensitive) ✅  
- `"navio"` → NÃO encontra (palavra diferente) ❌

**Teste manual**:
```sql
SELECT * FROM knowledge_chunks 
WHERE agent_id = 10 
  AND content ILIKE '%barco%';
```

## 🔬 Teste Manual Completo

```bash
# 1. Verificar chunks
./check_knowledge.sh

# 2. Se não houver chunks, fazer upload via curl
curl -X POST "http://localhost:8000/api/agents/10/knowledge/upload" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@teste.txt"

# 3. Verificar upload funcionou
psql -U corefoundry -d corefoundry -c "SELECT * FROM knowledge_chunks WHERE agent_id = 10;"

# 4. Testar chat
curl -X POST "http://localhost:8000/api/agents/10/chat" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"input":"Qual era a cor do barco?","thread_id":16,"use_knowledge":true}'

# 5. Observar logs do backend (terminal do uvicorn)
```

## 📊 SQL Queries Úteis

```sql
-- Total de chunks
SELECT COUNT(*) FROM knowledge_chunks;

-- Chunks por agent
SELECT agent_id, COUNT(*) 
FROM knowledge_chunks 
GROUP BY agent_id;

-- Buscar chunks de um agent
SELECT id, source, substring(content from 1 for 100) 
FROM knowledge_chunks 
WHERE agent_id = 10;

-- Testar busca
SELECT id, source, content 
FROM knowledge_chunks 
WHERE agent_id = 10 
  AND content ILIKE '%barco%';

-- Ver chunks sem agent_id (precisa migração)
SELECT COUNT(*) 
FROM knowledge_chunks 
WHERE agent_id IS NULL;
```

## 🎯 Próximos Passos (Melhorias)

Se mesmo após debugar o problema persistir, considere:

1. **Melhorar busca**: usar busca em múltiplos campos
```python
# Buscar em content + source + metadata
query_obj = self.db.query(KnowledgeChunk).filter(
    db.or_(
        KnowledgeChunk.content.ilike(f"%{query}%"),
        KnowledgeChunk.source.ilike(f"%{query}%")
    )
)
```

2. **Usar embeddings**: trocar busca ILIKE por vector search (pgvector)

3. **Aumentar limit**: mudar de 3 para 5 chunks

4. **Logar messages enviados ao Ollama**: ver exatamente o contexto montado

## 📁 Arquivos Modificados

- ✅ `corefoundry/app/routes/agents.py` - fix get_messages bug
- ✅ `corefoundry/app/services/agent_service.py` - logging detalhado
- ✅ `corefoundry/app/services/knowledge_service.py` - logging de busca
- ✅ `corefoundry/main.py` - configuração de logging
- ✅ `check_knowledge.sh` - script de verificação

## 🆘 Se Nada Funcionar

1. Compartilhe os logs completos do backend (desde startup até chat request)
2. Execute e compartilhe output: `./check_knowledge.sh > debug.txt`
3. Verifique: query SQL manual retorna chunks?
4. Frontend está enviando `use_knowledge: true` no payload?

---

**Última atualização**: 27/03/2026
**Versão**: 1.0
