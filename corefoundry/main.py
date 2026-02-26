"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Include routers
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(knowledge.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CoreFoundry",
        "version": "0.1.0",
        "description": "A simple way to build agents using LangChain and Ollama",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "agents": "/agents",
            "knowledge": "/knowledge"
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
