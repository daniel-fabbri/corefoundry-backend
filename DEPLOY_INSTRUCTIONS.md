# Deployment Instructions

## Servir Frontend + Backend no Mesmo Ngrok

### Arquitetura

```
ngrok → FastAPI Backend (port 8000)
         ├── /api/*        → Backend API routes
         ├── /health       → Health check
         └── /*            → Frontend (arquivos estáticos)
```

## Configuração do Backend

### 1. Instalar dependência para servir arquivos estáticos

```bash
pip install aiofiles
```

### 2. Modificar `corefoundry/main.py`

Adicione após as importações:

```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
```

Modifique os routers para usar prefixo `/api`:

```python
# Include routers with /api prefix
app.include_router(health.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
```

Adicione antes do `if __name__ == "__main__":`:

```python
# Serve static files (frontend)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend files, fallback to index.html for SPA routing."""
        file_path = os.path.join(static_dir, full_path)
        
        # Check if file exists
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Check for specific static files in root
        if full_path in ["favicon.svg", "icons.svg", ".nojekyll"]:
            root_file = os.path.join(static_dir, full_path)
            if os.path.isfile(root_file):
                return FileResponse(root_file)
        
        # SPA fallback - serve index.html for all other routes
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        
        return {"error": "Frontend not deployed. Run deploy.ps1 from frontend folder."}
```

Remova ou comente o endpoint root original (`@app.get("/")`).

## Deploy Workflow

### No Windows (onde está o código):

```powershell
cd corefoundry-frontend
.\deploy.ps1
```

### Copiar para o Linux Server:

```bash
# Do Windows, copie a pasta corefoundry-backend para o Linux
# Ou use rsync/scp se preferir
```

### No Linux Server:

```bash
cd ~/Documents/corefoundry-backend
source venv/bin/activate

# Instalar aiofiles se ainda não tiver
pip install aiofiles

# Iniciar backend (agora serve frontend também)
uvicorn corefoundry.main:app --host 0.0.0.0 --port 8000 --reload

# Em outro terminal, iniciar ngrok
ngrok http 8000
```

## Testar

Acesse o ngrok URL diretamente:
```
https://seu-ngrok-url.ngrok-free.app
```

- Frontend deve aparecer na raiz
- API acessível em `/api/health`, `/api/agents`, etc.

## Vantagens

✅ Um único ngrok endpoint  
✅ Sem CORS issues  
✅ Mais simples de gerenciar  
✅ Frontend e backend sempre sincronizados  
✅ Não precisa GitHub Pages  

## Atualizar Frontend

1. Faça mudanças no frontend (Windows)
2. Rode `.\deploy.ps1` 
3. Copie pasta `static` para o Linux server
4. Backend automaticamente serve a nova versão
