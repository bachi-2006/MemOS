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
    OLLAMA_BASE_URL: str = "http://172.27.112.1:11434"
    DEFAULT_LLM_MODEL: str = "qwen3.5:9b"
    DEFAULT_EMBEDDING_MODEL: str = "nomic-embed-text"

    if SettingsConfigDict:
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()


