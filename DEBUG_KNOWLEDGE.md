# 🐛 Debug do Knowledge Base - Guia Completo

## ✅ Bugs Corrigidos

### 1. AttributeError: 'AgentService' object has no attribute 'get_messages'
**Arquivo**: `corefoundry/app/routes/agents.py`
- **Problema**: Endpoint `/api/agents/{id}/history` chamava método inexistente
- **Solução**: Trocado `service.get_messages()` → `service.get_conversation_history()`

### 2. Busca de Knowledge não encontrando chunks
**Arquivo**: `corefoundry/app/services/knowledge_service.py`
- **Problema**: Busca procurava frase completa (ex: "qual era a cor da tela?") em vez de palavras-chave
- **Solução**: Implementada extração de keywords com remoção de stop words
  - Query: "qual era a cor da tela?" → Keywords: `['cor', 'tela']`
  - SQL: `WHERE (content ILIKE '%cor%' OR content ILIKE '%tela%')`
  - Agora encontra chunks que contenham QUALQUER palavra-chave relevante

### 3. Logs de Debug Implementados
**Arquivos**: 
- `corefoundry/app/services/agent_service.py`
- `corefoundry/app/services/knowledge_service.py`
- `corefoundry/main.py`

Agora o sistema loga:
- `use_knowledge` flag (true/false)
- Keywords extraídas da query
- Quantos chunks foram encontrados
- Preview de cada chunk (source, agent_id, conteúdo)
- Warnings quando nenhum chunk é encontrado
- Total de chunks no banco (para diagnóstico)
- Amostra do conteúdo dos chunks quando nenhum match é encontrado

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
[INFO] corefoundry.knowledge.search: Extracted keywords: ['cor', 'barco']
[INFO] corefoundry.knowledge.search: Filtering by agent_id=10
[INFO] corefoundry.knowledge.search: Search returned 1 chunks
[INFO] corefoundry.agent.chat: Found 1 relevant chunks
[INFO] corefoundry.agent.chat: Chunk[0]: id=42 source='teste.txt' agent_id=10 preview='O barco era vermelho\nA tela era azul'
[INFO] corefoundry.agent.chat: Adding context to messages (41 chars total)
```

### 🔍 Como Funciona a Busca por Keywords

A busca agora é **inteligente**:
1. Remove stop words (qual, era, a, o, da, do, etc)
2. Remove palavras muito curtas (< 3 caracteres)
3. Busca chunks que contenham **QUALQUER** palavra-chave

**Exemplo:**
```
Query: "qual era a cor da tela?"
Keywords extraídas: ['cor', 'tela']
SQL: WHERE (content ILIKE '%cor%' OR content ILIKE '%tela%')

Chunks encontrados:
✅ "A tela era azul" (contém 'tela')
✅ "A cor do barco é vermelha" (contém 'cor')
✅ "A tela e a cor estão definidas" (contém ambas)
❌ "O céu estava bonito" (não contém nenhuma)
```

**Teste a extração de keywords:**
```bash
cd ~/Documents/corefoundry-backend
python3 test_keywords.py
```

Se **NENHUM chunk** for encontrado:
```log
[INFO] corefoundry.knowledge.search: Extracted keywords: ['cor', 'tela']
[INFO] corefoundry.knowledge.search: Search returned 0 chunks
[WARNING] corefoundry.knowledge.search: No matches found! Total chunks in DB: 5, Chunks for agent_id=10: 2
[WARNING] corefoundry.knowledge.search: Sample chunk content: 'O barco era vermelho...'
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
A busca usa extração de keywords + `ILIKE` com OR:
- Query: `"qual era a cor da tela?"` → Keywords: `['cor', 'tela']`
- SQL: `WHERE (content ILIKE '%cor%' OR content ILIKE '%tela%')`
- `"A tela era azul"` → ✅ encontra (contém 'tela')
- `"A cor do barco"` → ✅ encontra (contém 'cor')  
- `"O céu estava bonito"` → ❌ NÃO encontra (nenhuma keyword)

**Se ainda não encontrar**, veja os logs:
```log
[INFO] Extracted keywords: ['cor', 'tela']
[WARNING] Sample chunk content: 'O barco era vermelho...'
```

Verifique se:
1. Keywords foram extraídas corretamente
2. Conteúdo do chunk realmente contém alguma keyword
3. Não há problema de encoding/acentuação

**Teste manual**:
```sql
-- Ver conteúdo real do chunk
SELECT id, source, content 
FROM knowledge_chunks 
WHERE agent_id = 10;

-- Testar busca por keyword individual
SELECT * FROM knowledge_chunks 
WHERE agent_id = 10 
  AND (content ILIKE '%cor%' OR content ILIKE '%tela%');
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

Se mesmo após a busca por keywords o problema persistir, considere:

1. **Usar embeddings**: trocar busca ILIKE por vector search (pgvector)
   - Busca semântica: "barco" encontra "embarcação"
   - Requer modelo de embeddings e extensão pgvector

2. **Aumentar limit**: mudar de 3 para 5-10 chunks
   - Mais contexto para o LLM
   - Mas pode aumentar latência

3. **Buscar em múltiplos campos**:
```python
# Buscar em content + source + metadata
query_obj = self.db.query(KnowledgeChunk).filter(
    db.or_(
        KnowledgeChunk.content.ilike(f"%{keyword}%"),
        KnowledgeChunk.source.ilike(f"%{keyword}%")
    )
)
```

4. **Ranqueamento por relevância**: ordenar chunks por número de keywords encontradas

5. **Logar messages enviados ao Ollama**: ver exatamente o contexto montado

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
