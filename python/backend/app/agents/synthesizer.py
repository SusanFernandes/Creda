"""
Synthesizer node — converts raw agent output (dicts/numbers) into natural language.

Defaults to the fast (8B) model first to avoid exhausting Groq 70B daily token limits.
Falls back to primary when configured, then to structured JSON text if both fail.
"""
import json
import logging

from app.config import settings
from app.core.llm import fast_llm, invoke_llm, primary_llm

logger = logging.getLogger("creda.synthesizer")

_SYNTH_PROMPT = """You are CREDA, a friendly AI financial coach for Indian users.
Merge the agent output below into ONE helpful, conversational response.

Rules:
- Respond ONLY in {language} (the user's language). If {language} is "en", respond in English.
- Lead with the most important insight or number.
- Use simple language — no jargon. Explain terms if needed.
- Include specific ₹ numbers from the data (don't round excessively).
- End with ONE clear, actionable step the user should take.
- Use ₹ for currency, not "Rs" or "INR".
{voice_instruction}

Agent used: {agent_used}
Agent output:
{agent_output}

User's original question: {message}

Your response (in {language}):"""

_SYNTH_SHORT = """You are CREDA. Summarize this financial agent output for the user in {language}.
Keep under {word_limit} words. Use ₹ for money. One clear next step at the end.

Agent: {agent_used}
Data (JSON):
{data}

User question: {message}

Response:"""

_VOICE_LINE = "- Keep under 200 words (this is a voice response — short and clear)."
_TEXT_LINE = "- Keep under 300 words."


def _compact_json(data: dict, limit: int = 2800) -> str:
    try:
        s = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        s = str(data)
    if len(s) > limit:
        return s[:limit] + "\n…"
    return s


async def synthesize(
    agent_output: dict,
    agent_used: str,
    message: str,
    language: str = "en",
    voice_mode: bool = False,
) -> str:
    """Convert raw agent output dict into user-facing natural language response."""
    compact_out = _compact_json(agent_output, 2800)
    word_limit = 120 if voice_mode else 200

    def _primary_prompt() -> str:
        return _SYNTH_PROMPT.format(
            language=language,
            voice_instruction=_VOICE_LINE if voice_mode else _TEXT_LINE,
            agent_used=agent_used,
            agent_output=compact_out,
            message=message or "",
        )

    def _fast_prompt() -> str:
        return _SYNTH_SHORT.format(
            language=language,
            word_limit=word_limit,
            agent_used=agent_used,
            data=compact_out,
            message=message or "",
        )

    if settings.GROQ_SYNTH_PRIMARY_FIRST:
        order: list[tuple[str, object, str]] = [
            ("primary", primary_llm, _primary_prompt()),
            ("fast", fast_llm, _fast_prompt()),
        ]
    else:
        order = [
            ("fast", fast_llm, _fast_prompt()),
            ("primary", primary_llm, _primary_prompt()),
        ]

    last_err: Exception | None = None
    for name, llm, prompt in order:
        try:
            result = await invoke_llm(llm, prompt)
            text = result.content.strip()
            if not text:
                continue
            if name == "fast" and not settings.GROQ_SYNTH_PRIMARY_FIRST and len(text) < 60:
                continue
            return text
        except Exception as e:
            last_err = e
            logger.warning("synthesize %s LLM failed (%s): %s", name, agent_used, e)

    if last_err:
        logger.warning("synthesize all models exhausted for %s", agent_used)
    return (
        "[CREDA] The AI wording service is temporarily unavailable (rate limit or network). "
        "Below is a structured summary of your results — you can still use every number shown.\n\n"
        + _compact_json(agent_output, 6000)
    )
