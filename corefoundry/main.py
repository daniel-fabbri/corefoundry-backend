"""Main FastAPI application."""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import httpx
from corefoundry.app.routes import health, agents, knowledge, auth
from corefoundry.configs.settings import settings

# API metadata
tags_metadata = [
    {
        "name": "health",
        "description": "Health check endpoints for monitoring the API status."
    },
    {
        "name": "auth",
        "description": "Authentication endpoints for user registration, login, and session management."
    },
    {
        "name": "agents",
        "description": "Manage AI agents, chat with them, and handle conversation threads."
    },
    {
        "name": "knowledge",
        "description": "Manage knowledge base for RAG (Retrieval Augmented Generation)."
    }
]

# Create FastAPI app
app = FastAPI(
    title="CoreFoundry API",
    description="""
## CoreFoundry - AI Agent Platform

Build and manage AI agents powered by LangChain and Ollama.

### Features

* 🤖 **Agent Management**: Create, update, and manage AI agents
* 💬 **Chat Interface**: Interactive conversations with agents
* 🧵 **Thread Management**: Organize conversations by topics
* 📚 **Knowledge Base**: Integrate RAG for enhanced responses
* 🔐 **Authentication**: Secure user authentication and authorization

### Authentication

Most endpoints require authentication using Bearer tokens. 
To authenticate:
1. Register a new account at `/api/auth/register`
2. Login at `/api/auth/login` to get an access token
3. Include the token in the Authorization header: `Bearer <token>`
    """,
    version="0.1.0",
    debug=settings.DEBUG,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=tags_metadata,
    openapi_url="/api/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")


# Development proxy to local frontend dev server
DEV_SERVER_URL = "http://127.0.0.1:5173"

@app.get("/test")
@app.get("/test/{full_path:path}")
async def proxy_frontend_dev(full_path: str = ""):
    """
    Reverse proxy to frontend dev server (Vite on port 5173).
    Proxies all requests under /test/ to the dev server, enabling
    full frontend functionality including hot reload.
    """
    target_url = f"{DEV_SERVER_URL}/{full_path}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(target_url)
            
            # Get content type and content
            media_type = resp.headers.get("content-type", "text/html")
            content = resp.content
            
            # For HTML responses, rewrite URLs to work through the proxy
            if "text/html" in media_type and full_path == "":
                content_str = content.decode("utf-8")
                # Replace absolute paths with /test prefix
                content_str = content_str.replace('href="/', 'href="/test/')
                content_str = content_str.replace('src="/', 'src="/test/')
                content_str = content_str.replace('from "/', 'from "/test/')
                content = content_str.encode("utf-8")
            
            return Response(
                content=content,
                media_type=media_type,
                status_code=resp.status_code
            )
    except httpx.ConnectError:
        return {
            "error": "Frontend dev server not running",
            "details": "Make sure to run 'npm run dev' in corefoundry-frontend",
            "url": DEV_SERVER_URL
        }
    except httpx.TimeoutException:
        return {
            "error": "Frontend dev server timeout",
            "url": DEV_SERVER_URL
        }
    except Exception as e:
        return {
            "error": "Could not reach frontend dev server",
            "details": str(e),
            "url": DEV_SERVER_URL
        }


# Proxy Vite-specific routes (for when not using /test prefix)
@app.get("/@vite/{full_path:path}")
@app.get("/@react-refresh")
@app.get("/src/{full_path:path}")
@app.get("/node_modules/{full_path:path}")
async def proxy_vite_assets(request: Request, full_path: str = ""):
    """Proxy Vite dev server assets that are requested without /test prefix."""
    # Get the full request path including query parameters
    request_path = request.url.path
    query_string = str(request.url.query) if request.url.query else ""
    target_url = f"{DEV_SERVER_URL}{request_path}"
    if query_string:
        target_url += f"?{query_string}"
    
    print(f"[PROXY] Requesting: {target_url}")  # Debug log
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(target_url)
            # Use the exact content-type from Vite server
            content_type = resp.headers.get("content-type", "application/javascript")
            
            print(f"[PROXY] Response content-type: {content_type}, status: {resp.status_code}")  # Debug log
            
            return Response(
                content=resp.content,
                media_type=content_type,
                status_code=resp.status_code
            )
    except Exception as e:
        print(f"[PROXY] Error: {str(e)}")  # Debug log
        return Response(content=f"Proxy error: {str(e)}".encode(), status_code=404)


# Serve static files (frontend)
# If a frontend build exists, always serve it from root.
# This guarantees same-origin behavior (e.g. ngrok -> backend -> frontend+api).
_main_dir = os.path.dirname(__file__)
_static_candidates = [
    os.getenv("FRONTEND_STATIC_DIR"),
    os.path.abspath(os.path.join(_main_dir, "..", "static")),
    os.path.abspath(os.path.join(_main_dir, "..", "..", "corefoundry-frontend", "dist")),
]
_static_candidates = [path for path in _static_candidates if path]
static_dir = next((path for path in _static_candidates if os.path.isdir(path)), None)

if static_dir:
    # Mount assets folder
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Serve frontend for all other routes  
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend files, fallback to index.html for SPA routing."""
        # Handle API docs
        if full_path.startswith("docs") or full_path.startswith("openapi"):
            # Let FastAPI handle /docs and /openapi.json
            return None
        
        # Try to serve the specific file
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # SPA fallback - serve index.html for all other routes
        index_path = os.path.join(static_dir, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        
        return {"error": "Frontend not deployed", "message": "Run deploy.ps1 from frontend folder"}
else:
    @app.get("/")
    async def root_fallback():
        """Root endpoint when frontend is not deployed."""
        return {
            "name": "CoreFoundry",
            "version": "0.1.0",
            "description": "A simple way to build agents using LangChain and Ollama",
            "status": "Frontend not deployed",
            "details": {
                "reason": "No frontend static directory found",
                "searched_paths": _static_candidates,
                "hint": "Set FRONTEND_STATIC_DIR or copy frontend build to one of the searched paths"
            },
            "endpoints": {
                "health": "/api/health",
                "docs": "/docs",
                "agents": "/api/agents",
                "knowledge": "/api/knowledge"
            }
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "corefoundry.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
