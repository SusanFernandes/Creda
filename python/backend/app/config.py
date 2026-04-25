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

    # ── LLM (Groq) ───────────────────────────────────────────
    GROQ_API_KEY: Optional[str] = None
    # Smaller max_tokens + input caps reduce TPD rate limits (on_demand tier is tight).
    GROQ_PRIMARY_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MAX_OUTPUT_TOKENS_PRIMARY: int = 768
    GROQ_MAX_OUTPUT_TOKENS_FAST: int = 512
    # Hard cap on prompt string length sent to Groq (characters, not tokens).
    GROQ_LLM_INPUT_MAX_CHARS: int = 10_000
    # If false: synthesizer uses fast model first (much lower token usage on 70B).
    GROQ_SYNTH_PRIMARY_FIRST: bool = False

    # ── TTS ────────────────────────────────────────────────
    KOKORO_TTS_URL: str = "http://localhost:8880"
    PIPER_TTS_URL: str = "http://localhost:8890"

    # ── STT ────────────────────────────────────────────────
    STT_ENGINE: str = "faster-whisper"
    WHISPER_MODEL_SIZE: str = "small"
    # Voice navigate / voice pipeline: try Groq Whisper API first (usually faster than local CPU).
    # Set false for fully offline voice (local faster-whisper only).
    STT_VOICE_GROQ_FIRST: bool = True
    # Groq transcription model (optional: try whisper-large-v3-turbo in .env for lower latency).
    GROQ_WHISPER_MODEL: str = "whisper-large-v3"

    # ── ChromaDB ───────────────────────────────────────────
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8030

    # ── Twilio (optional) ─────────────────────────────────
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_NUMBER: Optional[str] = None

    # POST /expenses from tools (e.g. WhatsApp “Create function”): if set, callers may send
    # X-Webhook-Secret or Authorization: Bearer <same value> instead of x-user-id.
    WHATSAPP_EXPENSE_WEBHOOK_SECRET: Optional[str] = None
    WHATSAPP_EXPENSE_USER_ID: str = "100"  # demo Arjun in creda_api users (see seed_demo)
    # Dev / tunnel only: if true, POST /expenses accepts no auth and always logs for WHATSAPP_EXPENSE_USER_ID.
    WHATSAPP_EXPENSE_TRUST_PUBLIC: bool = False

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
