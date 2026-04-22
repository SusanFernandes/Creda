"""
Redis client for CREDA — shared async connection pool, conversation history, caching.
"""
import json
import redis.asyncio as aioredis
from app.config import settings

# ── Shared connection pool (Issue 6 — never create per-request connections) ───
_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=20, decode_responses=True)


def get_redis() -> aioredis.Redis:
    """Return a Redis client backed by the shared connection pool."""
    return aioredis.Redis(connection_pool=_pool)


async def close_redis():
    """Drain pool on shutdown."""
    await _pool.disconnect()


# ── Conversation history (24h TTL) ────────────────────────────────────

CONV_TTL = 86400  # 24 hours


async def save_message(user_id: str, session_id: str, role: str, content: str):
    r = get_redis()
    key = f"conv:{user_id}:{session_id}"
    msg = json.dumps({"role": role, "content": content})
    await r.rpush(key, msg)
    await r.expire(key, CONV_TTL)


async def get_conversation(user_id: str, session_id: str, limit: int = 20) -> list[dict]:
    r = get_redis()
    key = f"conv:{user_id}:{session_id}"
    raw = await r.lrange(key, -limit, -1)
    return [json.loads(m) for m in raw]


# ── Generic cache ─────────────────────────────────────────────────────

async def cache_get(key: str) -> str | None:
    r = get_redis()
    return await r.get(f"cache:{key}")


async def cache_set(key: str, value: str, ttl: int = 3600):
    r = get_redis()
    await r.set(f"cache:{key}", value, ex=ttl)
