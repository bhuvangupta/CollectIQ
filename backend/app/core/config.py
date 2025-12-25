import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

# Get the project root directory (parent of backend)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class Settings(BaseSettings):
    # Application
    app_name: str = "Loan Collection Platform"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me-in-production"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "loan_collection"

    @property
    def database_url(self) -> str:
        if self.postgres_password:
            return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        return f"postgresql+asyncpg://{self.postgres_user}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def sync_database_url(self) -> str:
        if self.postgres_password:
            return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        return f"postgresql://{self.postgres_user}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # MinIO
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_root_user: str = "minio_admin"
    minio_root_password: str = "minio_password"
    minio_bucket: str = "loan-collection"
    minio_secure: bool = False

    # Celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    # AI Engine
    ai_engine_host: str = "localhost"
    ai_engine_port: int = 8001

    # LLM Provider
    llm_provider: str = "ollama"  # "ollama" or "groq"

    # Ollama (LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # Groq (LLM)
    groq_api_key: Optional[str] = None
    groq_model: str = "qwen-qwq-32b"

    # STT Provider
    stt_provider: str = "whisper"  # "whisper" or "groq"
    whisper_model: str = "base"
    groq_stt_model: str = "whisper-large-v3-turbo"

    # Frontend
    vite_api_url: str = "http://localhost:8000"

    @property
    def ai_engine_url(self) -> str:
        return f"http://{self.ai_engine_host}:{self.ai_engine_port}"

    # Telephony
    telephony_host: str = "localhost"
    telephony_port: int = 8002
    exotel_api_key: Optional[str] = None
    exotel_api_token: Optional[str] = None
    exotel_sid: Optional[str] = None
    exotel_subdomain: Optional[str] = None

    @property
    def telephony_url(self) -> str:
        return f"http://{self.telephony_host}:{self.telephony_port}"

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
