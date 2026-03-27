#!/bin/bash
# Script Ubuntu para verificar chunks de knowledge no banco

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔍 Verificando Knowledge Chunks no Banco${NC}"
echo "=========================================="
echo ""

# Ler variáveis do .env se existir
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Valores padrão
DB_USER=${POSTGRES_USER:-corefoundry}
DB_NAME=${POSTGRES_DB:-corefoundry}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# 1. Verificar se a coluna agent_id existe
echo -e "${YELLOW}1. Estrutura da tabela knowledge_chunks:${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\d knowledge_chunks"
echo ""

# 2. Contar total de chunks
echo -e "${YELLOW}2. Total de chunks no banco:${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) as total_chunks FROM knowledge_chunks;"
echo ""

# 3. Contar chunks por agent
echo -e "${YELLOW}3. Chunks por agent_id:${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT agent_id, COUNT(*) as chunk_count FROM knowledge_chunks GROUP BY agent_id ORDER BY agent_id;"
echo ""

# 4. Mostrar preview dos primeiros 5 chunks
echo -e "${YELLOW}4. Preview dos chunks (primeiros 5):${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT id, agent_id, source, substring(content from 1 for 100) as preview FROM knowledge_chunks ORDER BY created_at DESC LIMIT 5;"
echo ""

# 5. Testar busca (exemplo)
echo -e "${YELLOW}5. Teste de busca (palavra 'barco'):${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT id, agent_id, source, substring(content from 1 for 150) as preview FROM knowledge_chunks WHERE content ILIKE '%barco%';"
echo ""

echo -e "${GREEN}✅ Verificação completa!${NC}"
echo ""
echo -e "${YELLOW}Dicas:${NC}"
echo "- Se não há chunks, faça upload via interface"
echo "- Se agent_id é NULL, rode a migração: ./migrate_knowledge.sh"
echo "- Para ver chunks de um agent específico:"
echo "  psql -U $DB_USER -d $DB_NAME -c \"SELECT * FROM knowledge_chunks WHERE agent_id = X;\""
