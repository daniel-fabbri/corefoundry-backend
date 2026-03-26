"""Main FastAPI application."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import httpx
from corefoundry.app.routes import health, agents, knowledge
from corefoundry.configs.settings import settings

# Create FastAPI app
app = FastAPI(
    title="CoreFoundry",
    description="A simple way to build agents using LangChain and Ollama",
    version="0.1.0",
    debug=settings.DEBUG
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
app.include_router(agents.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")


# Serve static files (frontend)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_dir):
    # Mount assets folder
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
    
    # Development proxy/test route to fetch frontend from local dev server
    @app.get("/test")
    async def test_local_frontend():
        """Fetch the frontend bundle from a local dev server (localhost:5173).
        Useful when running the frontend with `npm run dev` and testing via the API host.
        """
        dev_url = "http://localhost:5174/"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(dev_url)
                media_type = resp.headers.get("content-type", "text/html")
                return Response(content=resp.content, media_type=media_type, status_code=resp.status_code)
        except Exception:
            # Fallback message if the dev server is not reachable
            return {"error": "Could not reach frontend dev server at http://localhost:5174"}
    
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
