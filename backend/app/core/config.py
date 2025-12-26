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

    # MinIO - credentials required via environment variables
    minio_host: str = "localhost"
    minio_port: int = 9000
    minio_root_user: Optional[str] = None  # Required: set MINIO_ROOT_USER
    minio_root_password: Optional[str] = None  # Required: set MINIO_ROOT_PASSWORD
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
    llm_provider: str = "sarvam"  # "ollama", "groq", or "sarvam"

    # Ollama (LLM)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    # Groq (LLM)
    groq_api_key: Optional[str] = None
    groq_model: str = "qwen/qwen3-32b"

    # STT Provider
    stt_provider: str = "sarvam"  # "whisper", "groq", or "sarvam"
    whisper_model: str = "base"
    groq_stt_model: str = "whisper-large-v3-turbo"

    # TTS Provider
    tts_provider: str = "sarvam"  # "sarvam", "elevenlabs", or "local"

    # Sarvam AI (LLM, STT, TTS)
    sarvam_api_key: Optional[str] = None
    sarvam_llm_model: str = "sarvam-m"
    sarvam_stt_model: str = "saarika:v2"
    sarvam_tts_model: str = "bulbul:v2"
    sarvam_tts_voice: str = "Anushka"
    sarvam_stt_language: str = "hi-IN"
    sarvam_tts_language: str = "hi-IN-HINGLISH"

    # ElevenLabs (TTS fallback)
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None

    # Deepgram (STT/TTS)
    deepgram_api_key: Optional[str] = None

    # Cartesia (TTS)
    cartesia_api_key: Optional[str] = None

    # OpenAI
    openai_api_key: Optional[str] = None

    # Frontend
    vite_api_url: str = "http://localhost:8000"

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:80"

    @property
    def ai_engine_url(self) -> str:
        return f"http://{self.ai_engine_host}:{self.ai_engine_port}"

    # Telephony (integrated into backend)
    telephony_provider: str = "mock"  # "mock" or "exotel"
    exotel_api_key: Optional[str] = None
    exotel_api_token: Optional[str] = None
    exotel_sid: Optional[str] = None
    exotel_subdomain: Optional[str] = None
    exotel_caller_id: Optional[str] = None
    exotel_sms_sender_id: str = "LNCOLL"
    exotel_webhook_url: Optional[str] = None

    # SMS/WhatsApp Provider
    sms_provider: str = "mock"  # "mock", "gupshup", "exotel"

    # Voice AI Provider
    voice_ai_provider: str = "livekit"  # "bolna", "livekit", "sarvam"
    bolna_api_key: Optional[str] = None
    bolna_agent_id: Optional[str] = None
    voice_ai_webhook_url: Optional[str] = None

    # LiveKit (for real-time voice AI)
    livekit_url: str = "wss://your-project.livekit.cloud"
    livekit_api_key: Optional[str] = None
    livekit_api_secret: Optional[str] = None

    # Gupshup (for WhatsApp Business API)
    gupshup_api_key: Optional[str] = None
    gupshup_app_name: Optional[str] = None
    gupshup_source_number: Optional[str] = None

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
