"""
CREDA FastAPI Backend — main application.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.redis_client import get_redis, close_redis

logger = logging.getLogger("creda")


async def _init_chromadb_if_empty():
    """Load knowledge/documents.yaml into ChromaDB if collection is empty."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection("creda_knowledge")
        if collection.count() == 0:
            from app.services.rag import load_knowledge_base
            await load_knowledge_base(client)
            logger.info("ChromaDB: loaded knowledge base documents")
        else:
            logger.info("ChromaDB: collection already has %d documents", collection.count())
    except Exception as e:
        logger.warning("ChromaDB init skipped (will retry on first RAG query): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Structured logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("CREDA FastAPI starting on port %s", settings.FASTAPI_PORT)

    # Create tables if they don't exist (Alembic preferred in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Verify Redis connection
    try:
        r = get_redis()
        await r.ping()
        logger.info("Redis: connected")
    except Exception as e:
        logger.warning("Redis: connection failed — %s", e)

    # Load knowledge base into ChromaDB
    await _init_chromadb_if_empty()

    # Start nudge scheduler
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from app.services.nudge_worker import run_nudge_checks, run_premarket_briefing
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_nudge_checks, "cron", hour=9, minute=0, id="daily_nudges")
    scheduler.add_job(run_nudge_checks, "interval", hours=6, id="periodic_nudges")
    scheduler.add_job(run_premarket_briefing, "cron", hour=9, minute=15, id="premarket_briefing")
    from app.core.scheduler import register_data_jobs

    register_data_jobs(scheduler)
    scheduler.start()
    logger.info("Nudge scheduler: started (daily 9AM + every 6h + pre-market 9:15AM + data crawlers)")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    await close_redis()
    await engine.dispose()
    logger.info("CREDA FastAPI shut down")


app = FastAPI(
    title="CREDA API",
    description="AI-powered multilingual financial coach for India",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — env-driven origins
_cors_origins = settings.CORS_ORIGINS.split(",") if hasattr(settings, "CORS_ORIGINS") and settings.CORS_ORIGINS else ["http://localhost:8000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount routers ──────────────────────────────────────────────────────
from app.routers import auth, profile, chat, voice, portfolio, agents, nudges, whatsapp, compliance, family, assumptions  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(assumptions.router, prefix="/assumptions", tags=["assumptions"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(nudges.router, prefix="/nudges", tags=["nudges"])
app.include_router(whatsapp.router, prefix="/whatsapp", tags=["whatsapp"])
app.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
app.include_router(family.router, prefix="/family", tags=["family"])


@app.get("/health")
async def health():
    """Check all dependencies — PostgreSQL, Redis, ChromaDB, Kokoro TTS."""
    checks: dict = {}

    # PostgreSQL
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # ChromaDB
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        client.heartbeat()
        checks["chromadb"] = "ok"
    except Exception as e:
        checks["chromadb"] = f"error: {e}"

    # Kokoro TTS
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as c:
            resp = await c.get(f"{settings.KOKORO_TTS_URL}/health")
            checks["kokoro_tts"] = "ok" if resp.status_code == 200 else f"status: {resp.status_code}"
    except Exception as e:
        checks["kokoro_tts"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "service": "creda-backend", "version": "2.0.0", "checks": checks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.FASTAPI_PORT, reload=True)
