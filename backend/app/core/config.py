try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None

class Settings(BaseSettings):
    PROJECT_NAME: str = "MemOS"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super_secret_memos_key_change_in_production_32bytes"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # Database
    DATABASE_URL: str = "postgresql://memos_user:memos_password@localhost:5432/memos_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector & Graph DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "memos_password"

    # Ollama Local Integration
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    PROXY_HOST: str = "127.0.0.1"
    PROXY_PORT: int = 11435
    DEFAULT_LLM_MODEL: str = "qwen3.5:9b"
    DEFAULT_EMBEDDING_MODEL: str = "nomic-embed-text"

    # CORS & Security
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000", "*"]

    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()


