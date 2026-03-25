"""Health check routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import traceback

from corefoundry.app.db.connection import get_db
from corefoundry.app.services.ollama_service import ollama_service

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint.

    Returns status of the application and its dependencies.
    """
    # Check database connection
    db_healthy = True
    try:
        # Use a text() SQL expression to ensure compatibility with SQLAlchemy
        db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False
        traceback.print_exc()

    # Check Ollama connection
    ollama_healthy = await ollama_service.check_health()

    status = "ok" if (db_healthy and ollama_healthy) else "degraded"

    return {
        "status": status,
        "database": "healthy" if db_healthy else "unhealthy",
        "ollama": "healthy" if ollama_healthy else "unhealthy"
    }
