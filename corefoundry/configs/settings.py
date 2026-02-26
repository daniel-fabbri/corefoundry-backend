"""Application settings and configuration."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/corefoundry"
    )

    # Ollama
    OLLAMA_HOST: str = os.getenv(
        "OLLAMA_HOST",
        "http://localhost:11434"
    )

    # Optional external URLs
    NGROK_URL: Optional[str] = os.getenv("NGROK_URL")
    CLOUDFLARE_TUNNEL_URL: Optional[str] = os.getenv("CLOUDFLARE_TUNNEL_URL")

    # Application
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Ollama default model
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")


settings = Settings()
