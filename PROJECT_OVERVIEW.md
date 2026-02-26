# CoreFoundry - Project Overview

## Structure Created

### Core Application (`corefoundry/`)

#### Configuration (`configs/`)
- `settings.py` - Application settings with environment variable support
  - Database configuration
  - Ollama host configuration
  - Application settings (host, port, debug)
  - Optional ngrok/Cloudflare tunnel URLs

#### Database Layer (`app/db/`)
- `connection.py` - Database connection management
  - SQLAlchemy engine setup
  - Session factory
  - `get_db()` dependency for FastAPI
  - `init_db()` for table creation
  
- `models.py` - Database models
  - **Agent** - Store agent configurations
  - **Message** - Chat history
  - **Memory** - Agent memory
  - **KnowledgeChunk** - Knowledge base chunks

#### Services (`app/services/`)
- `ollama_service.py` - Ollama API integration
  - List available models
  - Run prompts
  - Chat interface
  - Health check
  
- `agent_service.py` - Agent management
  - Create/read/delete agents
  - Chat with agents
  - Manage conversation history
  - Integration with memory and knowledge base
  
- `memory_service.py` - Memory management
  - Save/retrieve memory entries
  - Update existing memories
  - Clear memories
  
- `knowledge_service.py` - Knowledge base management
  - Upload text (with automatic chunking)
  - Search knowledge chunks
  - Manage knowledge entries

#### API Routes (`app/routes/`)
- `health.py` - Health check endpoints
  - `/health` - Application and dependency status
  
- `agents.py` - Agent endpoints
  - `POST /agents/create` - Create new agent
  - `GET /agents/{agent_id}` - Get agent details
  - `GET /agents/` - List all agents
  - `POST /agents/{agent_id}/chat` - Chat with agent
  - `GET /agents/{agent_id}/history` - Get conversation history
  - `DELETE /agents/{agent_id}` - Delete agent
  
- `knowledge.py` - Knowledge base endpoints
  - `POST /knowledge/upload` - Upload text to knowledge base
  - `POST /knowledge/search` - Search knowledge base
  - `GET /knowledge/chunks` - List knowledge chunks
  - `DELETE /knowledge/chunks/{chunk_id}` - Delete chunk
  - `DELETE /knowledge/source/{source}` - Delete all chunks from source

#### Main Application
- `main.py` - FastAPI application
  - CORS middleware
  - Router registration
  - Root endpoint with API documentation

### Supporting Files

#### Scripts
- `run.sh` - Start production server
- `dev.sh` - Start development server with hot reload
- `init_db.sh` - Initialize database tables

#### Configuration
- `.env.example` - Example environment variables
- `requirements.txt` - Python dependencies
- `setup.py` - Package setup file

#### Docker
- `Dockerfile` - Container image definition
- `docker-compose.yml` - Multi-service orchestration

#### Documentation
- `README.md` - Comprehensive usage guide
- `DEPLOYMENT.md` - Deployment instructions

#### Testing
- `test_basic.py` - Basic functionality tests

## Key Features

### 1. Modular Architecture
- Separation of concerns (routes, services, models)
- Easy to extend and maintain
- Clear dependency injection

### 2. Database Integration
- PostgreSQL with SQLAlchemy ORM
- Automatic table creation
- Relationship management

### 3. LangChain Integration
- Text splitting for knowledge base
- Conversation management
- Memory system

### 4. Ollama Integration
- Direct API communication
- Model listing
- Chat and generation support

### 5. RESTful API
- FastAPI with automatic documentation
- Request/response validation with Pydantic
- Proper error handling

### 6. Developer Experience
- Type hints throughout
- Comprehensive docstrings
- Example environment file
- Multiple deployment options

## API Endpoints Summary

### Health
- `GET /health` - Check application health

### Agents
- `POST /agents/create` - Create agent
- `GET /agents/` - List agents
- `GET /agents/{id}` - Get agent
- `POST /agents/{id}/chat` - Chat with agent
- `GET /agents/{id}/history` - Get history
- `DELETE /agents/{id}` - Delete agent

### Knowledge
- `POST /knowledge/upload` - Upload knowledge
- `POST /knowledge/search` - Search knowledge
- `GET /knowledge/chunks` - List chunks
- `DELETE /knowledge/chunks/{id}` - Delete chunk
- `DELETE /knowledge/source/{source}` - Delete by source

## Database Schema

### agents
- id (PK)
- name
- description
- model_name
- config (JSON)
- created_at
- updated_at

### messages
- id (PK)
- agent_id (FK)
- role (user/assistant/system)
- content
- message_metadata (JSON)
- created_at

### memory
- id (PK)
- agent_id (FK)
- key
- value
- memory_metadata (JSON)
- created_at
- updated_at

### knowledge_chunks
- id (PK)
- content
- source
- chunk_metadata (JSON)
- embedding
- created_at

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string
- `OLLAMA_HOST` - Ollama server URL

Optional:
- `OLLAMA_MODEL` - Default model (default: llama2)
- `APP_HOST` - Server host (default: 0.0.0.0)
- `APP_PORT` - Server port (default: 8000)
- `DEBUG` - Debug mode (default: false)
- `NGROK_URL` - ngrok tunnel URL
- `CLOUDFLARE_TUNNEL_URL` - Cloudflare tunnel URL

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. Initialize database:
   ```bash
   ./init_db.sh
   ```

4. Start server:
   ```bash
   ./dev.sh
   ```

5. Access API:
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## Testing

Run tests:
```bash
pytest test_basic.py -v
```

All tests pass successfully without warnings.

## Next Steps

The foundation is complete. Future enhancements could include:
- Authentication and authorization
- Vector embeddings for semantic search
- WebSocket support for streaming responses
- Caching layer (Redis)
- Rate limiting
- API versioning
- Comprehensive test suite
- CI/CD pipeline
- Monitoring and observability
