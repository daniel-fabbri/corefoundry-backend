# CoreFoundry Backend

CoreFoundry é uma camada simples, modular e escalável para criar agentes de IA usando LangChain e Ollama. O projeto permite gerenciar agentes, armazenar histórico de conversas, memória e base de conhecimento em PostgreSQL, tudo integrado com Ollama rodando localmente.

## 🚀 Características

- **FastAPI**: Backend rápido e moderno
- **LangChain**: Framework para construção de agentes de IA
- **Ollama**: Execução local de LLMs
- **PostgreSQL**: Armazenamento de dados, histórico e conhecimento
- **Modular**: Arquitetura escalável e organizada

## 📋 Pré-requisitos

- Python 3.10+
- PostgreSQL 12+
- Ollama instalado e rodando

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/daniel-fabbri/corefoundry-backend.git
cd corefoundry-backend
```

### 2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e ajuste conforme necessário:

```bash
cp .env.example .env
```

Edite o arquivo `.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/corefoundry

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
```

### 5. Configure o PostgreSQL

Crie um banco de dados:

```bash
createdb corefoundry
```

Ou via SQL:

```sql
CREATE DATABASE corefoundry;
```

### 6. Inicialize o banco de dados

```bash
./init_db.sh
```

## 🎯 Como Configurar o Ollama

### Instalar o Ollama no Ubuntu

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Baixar um modelo

```bash
ollama pull llama2
# ou outro modelo de sua preferência
ollama pull mistral
ollama pull codellama
```

### Verificar se está rodando

```bash
curl http://localhost:11434/api/tags
```

### Expor o Ollama via ngrok (opcional)

Se quiser acessar o Ollama de fora da sua rede:

```bash
ngrok http 11434
```

Atualize a variável `OLLAMA_HOST` no `.env` com a URL do ngrok.

## 🏃 Como Rodar

### Modo de produção

```bash
./run.sh
```

### Modo de desenvolvimento (com hot reload)

```bash
./dev.sh
```

A API estará disponível em `http://localhost:8000`

## 📚 Documentação da API

Após iniciar o servidor, acesse:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤖 Como Usar

### 1. Verificar o status da aplicação

```bash
curl http://localhost:8000/health
```

Resposta:
```json
{
  "status": "ok",
  "database": "healthy",
  "ollama": "healthy"
}
```

### 2. Criar seu primeiro agente

```bash
curl -X POST http://localhost:8000/agents/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Assistente Pessoal",
    "description": "Um assistente amigável",
    "model_name": "llama2",
    "config": {
      "temperature": 0.7,
      "system_prompt": "Você é um assistente prestativo e amigável."
    }
  }'
```

Resposta:
```json
{
  "id": 1,
  "name": "Assistente Pessoal",
  "description": "Um assistente amigável",
  "model_name": "llama2",
  "config": {
    "temperature": 0.7,
    "system_prompt": "Você é um assistente prestativo e amigável."
  },
  "created_at": "2026-02-26T14:50:00.000000"
}
```

### 3. Enviar uma mensagem ao agente

```bash
curl -X POST http://localhost:8000/agents/1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Olá! Como você pode me ajudar?",
    "use_knowledge": false
  }'
```

Resposta:
```json
{
  "response": "Olá! Estou aqui para ajudar você...",
  "metadata": {
    "model": "llama2",
    "agent_id": 1,
    "agent_name": "Assistente Pessoal"
  }
}
```

### 4. Listar todos os agentes

```bash
curl http://localhost:8000/agents/
```

### 5. Ver histórico de conversa

```bash
curl http://localhost:8000/agents/1/history
```

### 6. Trabalhar com base de conhecimento

#### Fazer upload de conhecimento

```bash
curl -X POST http://localhost:8000/knowledge/upload \
  -H "Content-Type: application/json" \
  -d '{
    "text": "CoreFoundry é uma plataforma para criar agentes de IA...",
    "source": "documentação",
    "metadata": {
      "category": "docs",
      "version": "1.0"
    }
  }'
```

Resposta:
```json
{
  "message": "Knowledge uploaded successfully",
  "chunks_created": 1,
  "chunk_ids": [1]
}
```

#### Buscar na base de conhecimento

```bash
curl -X POST http://localhost:8000/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "CoreFoundry",
    "limit": 5
  }'
```

#### Usar conhecimento em uma conversa

```bash
curl -X POST http://localhost:8000/agents/1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "input": "O que é CoreFoundry?",
    "use_knowledge": true
  }'
```

## 📁 Estrutura do Projeto

```
corefoundry/
├── app/
│   ├── __init__.py
│   ├── routes/              # Rotas da API
│   │   ├── __init__.py
│   │   ├── agents.py        # Endpoints de agentes
│   │   ├── health.py        # Health check
│   │   └── knowledge.py     # Endpoints de conhecimento
│   ├── services/            # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── agent_service.py
│   │   ├── knowledge_service.py
│   │   ├── memory_service.py
│   │   └── ollama_service.py
│   └── db/                  # Camada de dados
│       ├── __init__.py
│       ├── connection.py    # Conexão e sessão
│       ├── models.py        # Modelos SQLAlchemy
│       └── migrations/      # Migrações (futuro)
├── configs/
│   ├── __init__.py
│   └── settings.py          # Configurações
├── main.py                  # Aplicação FastAPI
└── __init__.py
```

## 🛠️ Arquitetura

### Banco de Dados

O projeto utiliza 4 tabelas principais:

1. **agents**: Armazena configurações dos agentes
2. **messages**: Histórico de mensagens
3. **memory**: Memória dos agentes
4. **knowledge_chunks**: Base de conhecimento

### Serviços

- **AgentService**: Gerencia criação e interação com agentes
- **OllamaService**: Interface com a API do Ollama
- **MemoryService**: Gerencia memória dos agentes
- **KnowledgeService**: Gerencia base de conhecimento

## 🔒 Segurança

Em produção:

1. Use variáveis de ambiente seguras
2. Configure CORS adequadamente
3. Use HTTPS
4. Proteja o banco de dados com senhas fortes
5. Implemente autenticação e autorização

## 🚢 Deploy

### Com Docker (futuro)

```bash
docker-compose up -d
```

### Manual

1. Configure um servidor PostgreSQL
2. Configure o Ollama
3. Configure variáveis de ambiente
4. Execute `./run.sh`

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📧 Contato

Daniel Fabbri - [@daniel-fabbri](https://github.com/daniel-fabbri)

Link do Projeto: [https://github.com/daniel-fabbri/corefoundry-backend](https://github.com/daniel-fabbri/corefoundry-backend)
