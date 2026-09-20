from typing import List
import os

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _HAS_PYDANTIC_SETTINGS = True
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None
    _HAS_PYDANTIC_SETTINGS = False

# Resolve .env path relative to the project root (backend/app/core/config.py -> project root)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

def _load_env_file() -> None:
    """Load .env into os.environ if present. Works even without pydantic-settings."""
    if not os.path.exists(ENV_FILE):
        return
    try:
        try:
            from dotenv import load_dotenv
            load_dotenv(ENV_FILE)
            return
        except ImportError:
            pass
        # Fallback: minimal .env parser (KEY=VALUE lines, quotes stripped)
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except Exception:
        pass

_load_env_file()

class Settings(BaseSettings):
    PROJECT_NAME: str = "MemOS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = "postgresql://memos_user@localhost:5432/memos_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector & Graph DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    # Ollama Local Integration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    PROXY_HOST: str = "127.0.0.1"
    PROXY_PORT: int = 11435
    DEFAULT_LLM_MODEL: str = ""
    DEFAULT_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Companion Mode & Security
    COMPANION_MODE: bool = True  # Allows anonymous local loopback single-user companion mode

    # CORS & Security — strictly explicit origins, no wildcards
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5151",
        "http://127.0.0.1:5151",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    if _HAS_PYDANTIC_SETTINGS and SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=ENV_FILE,
            extra="ignore"
        )

    def __init__(self, **kwargs):
        # If pydantic-settings is unavailable (plain pydantic BaseModel fallback),
        # read known env vars from os.environ into the model fields.
        if not _HAS_PYDANTIC_SETTINGS:
            for field_name in self.model_fields:
                env_val = os.environ.get(field_name)
                if env_val is not None and kwargs.get(field_name) is None:
                    kwargs[field_name] = env_val
        super().__init__(**kwargs)
        if not self.SECRET_KEY:
            raise RuntimeError(
                "Missing required SECRET_KEY. Add SECRET_KEY to your .env file. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )

settings = Settings()
