# PowerShell script para executar a migração do knowledge base

Write-Host "🚀 CoreFoundry - Migração Knowledge Base" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se o PostgreSQL está rodando
Write-Host "📊 Verificando configuração..." -ForegroundColor Yellow

# Ler variáveis do .env se existir
$envFile = ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -notmatch '^#' -and $_ -match '=' } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key, $value, 'Process')
    }
}

# Valores padrão se não estiverem no .env
$DB_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "corefoundry" }
$DB_NAME = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "corefoundry" }
$DB_HOST = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$DB_PORT = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }

Write-Host "Host: $DB_HOST" -ForegroundColor Gray
Write-Host "Port: $DB_PORT" -ForegroundColor Gray
Write-Host "Database: $DB_NAME" -ForegroundColor Gray
Write-Host "User: $DB_USER" -ForegroundColor Gray
Write-Host ""

# Verificar se psql está disponível
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue

if (-not $psqlPath) {
    Write-Host "❌ psql não encontrado no PATH. Opções:" -ForegroundColor Red
    Write-Host ""
    Write-Host "1. Instalar PostgreSQL client tools" -ForegroundColor Yellow
    Write-Host "2. Usar Docker:" -ForegroundColor Yellow
    Write-Host "   docker exec -i postgres_container psql -U $DB_USER -d $DB_NAME < migrate_add_agent_to_knowledge.sql" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "3. Usar pgAdmin ou outra ferramenta GUI" -ForegroundColor Yellow
    exit 1
}

# Executar migração
Write-Host "📝 Executando migração..." -ForegroundColor Yellow
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
& psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrate_add_agent_to_knowledge.sql

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Migração executada com sucesso!" -ForegroundColor Green
    Write-Host ""
    
    # Verificar se a coluna foi adicionada
    Write-Host "🔍 Verificando estrutura da tabela..." -ForegroundColor Yellow
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\d knowledge_chunks"
    
    Write-Host ""
    Write-Host "📁 Criando diretório de uploads..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path "uploads" | Out-Null
    Write-Host "✅ Diretório criado: .\uploads" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "🎉 Tudo pronto! Reinicie o backend para aplicar as mudanças." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Erro ao executar migração. Verifique:" -ForegroundColor Red
    Write-Host "   - PostgreSQL está rodando?" -ForegroundColor Yellow
    Write-Host "   - Credenciais corretas no .env?" -ForegroundColor Yellow
    Write-Host "   - Banco de dados existe?" -ForegroundColor Yellow
}
