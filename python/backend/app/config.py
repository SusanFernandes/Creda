"""
CREDA FastAPI backend — centralised configuration from environment.
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ───────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://creda_admin:creda_secure_2025@localhost:8010/creda_api"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return self.DATABASE_URL.replace("+asyncpg", "").replace("asyncpg://", "postgresql://")

    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:8020/0"

    # ── Auth ───────────────────────────────────────────────
    JWT_SECRET: str = "change-me-in-production"

    # ── LLM ────────────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None

    # ── TTS ────────────────────────────────────────────────
    KOKORO_TTS_URL: str = "http://localhost:8880"
    PIPER_TTS_URL: str = "http://localhost:8890"

    # ── STT ────────────────────────────────────────────────
    STT_ENGINE: str = "faster-whisper"
    WHISPER_MODEL_SIZE: str = "small"

    # ── ChromaDB ───────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8030

    # ── Twilio (optional) ─────────────────────────────────
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # ── Server ─────────────────────────────────────────────
    FASTAPI_PORT: int = 8001
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:8000"

    # ── Rate Limiting ─────────────────────────────────────
    RATE_LIMIT_LOGIN: int = 5  # per minute
    RATE_LIMIT_REGISTER: int = 3  # per minute

    model_config = {
        "env_file": ["../.env", ".env"],
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
