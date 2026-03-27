#!/bin/bash
# Script para executar a migração do knowledge base

echo "🚀 CoreFoundry - Migração Knowledge Base"
echo "=========================================="
echo ""

# Verificar se o PostgreSQL está rodando
echo "📊 Verificando conexão com PostgreSQL..."

# Ler variáveis do .env se existir
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Valores padrão se não estiverem no .env
DB_USER=${POSTGRES_USER:-corefoundry}
DB_NAME=${POSTGRES_DB:-corefoundry}
DB_HOST=${POSTGRES_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}

echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Executar migração
echo "📝 Executando migração..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrate_add_agent_to_knowledge.sql

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migração executada com sucesso!"
    echo ""
    
    # Verificar se a coluna foi adicionada
    echo "🔍 Verificando estrutura da tabela..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\d knowledge_chunks"
    
    echo ""
    echo "📁 Criando diretório de uploads..."
    mkdir -p uploads
    chmod 755 uploads
    echo "✅ Diretório criado: ./uploads"
    
    echo ""
    echo "🎉 Tudo pronto! Reinicie o backend para aplicar as mudanças."
else
    echo ""
    echo "❌ Erro ao executar migração. Verifique:"
    echo "   - PostgreSQL está rodando?"
    echo "   - Credenciais corretas no .env?"
    echo "   - Banco de dados existe?"
fi
