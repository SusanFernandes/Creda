"""
Singleton Groq LLM clients — created once at import, reused everywhere.

Never instantiate ChatGroq per agent call. Import from here:
    from app.core.llm import primary_llm, fast_llm, invoke_llm, clip_prompt

Use ``invoke_llm`` for all Groq calls so prompts are clipped and 429s get backoff
plus a one-shot fallback from primary → fast model.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from langchain_groq import ChatGroq

from app.config import settings

logger = logging.getLogger("creda.llm")

# llama-3.3-70b — heavier reasoning (tight max_tokens to limit completion TPD)
primary_llm = ChatGroq(
    model=settings.GROQ_PRIMARY_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0.3,
    max_retries=1,
    max_tokens=settings.GROQ_MAX_OUTPUT_TOKENS_PRIMARY,
)

# llama-3.1-8b — fast / cheap; default for many short tasks when routed explicitly
fast_llm = ChatGroq(
    model=settings.GROQ_FAST_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0,
    max_retries=1,
    max_tokens=settings.GROQ_MAX_OUTPUT_TOKENS_FAST,
)


def clip_prompt(text: str, max_chars: int | None = None) -> str:
    """Truncate user/agent-built strings before sending to Groq."""
    if not text:
        return text
    mc = max_chars if max_chars is not None else settings.GROQ_LLM_INPUT_MAX_CHARS
    if len(text) <= mc:
        return text
    return text[: mc - 80] + "\n\n[... truncated for token budget ...]"


def _is_rate_limit(exc: BaseException) -> bool:
    s = str(exc).lower()
    return "429" in str(exc) or "rate_limit" in s or "too many requests" in s


async def invoke_llm(llm: ChatGroq, prompt: str | Any, *, clip: bool = True) -> Any:
    """
    Invoke Groq with input clipping, short backoff on 429, and primary→fast fallback.

    Always prefer this over raw ``.ainvoke`` for user-facing features.
    """
    if not isinstance(prompt, str):
        prompt = str(prompt)
    if clip:
        prompt = clip_prompt(prompt)

    backoff = (0.0, 2.0, 6.0)
    last_err: BaseException | None = None
    for attempt, delay in enumerate(backoff):
        if delay:
            await asyncio.sleep(delay)
        try:
            return await llm.ainvoke(prompt)
        except BaseException as e:
            last_err = e
            if _is_rate_limit(e) and attempt < len(backoff) - 1:
                logger.warning(
                    "Groq rate limit (%s, attempt %s/%s): %s",
                    getattr(llm, "model_name", "?"),
                    attempt + 1,
                    len(backoff),
                    e,
                )
                continue
            if not _is_rate_limit(e):
                raise
            break

    if (
        last_err
        and llm is primary_llm
        and _is_rate_limit(last_err)
    ):
        try:
            short_p = clip_prompt(prompt, min(settings.GROQ_LLM_INPUT_MAX_CHARS, 6000))
            logger.info("Groq: falling back to fast_llm after primary rate limit")
            return await invoke_llm(fast_llm, short_p, clip=False)
        except BaseException as e2:
            logger.warning("Groq fast_llm fallback failed: %s", e2)
            raise last_err from e2

    if last_err:
        raise last_err
    raise RuntimeError("invoke_llm: unexpected empty path")
