from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load server/.env regardless of cwd
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


@lru_cache
def get_settings() -> "Settings":
    return Settings()


class Settings:
    """App settings loaded from environment / .env."""

    def __init__(self) -> None:
        self.ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1").strip()
        self.ollama_base_url: str = os.getenv(
            "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
        ).strip()
        self.cors_origins: list[str] = [
            o.strip()
            for o in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if o.strip()
        ]


settings = get_settings()