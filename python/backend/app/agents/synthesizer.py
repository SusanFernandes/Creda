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

AUTHORITATIVE USER FACTS (loaded from the database for this user — never contradict with invented figures):
{user_facts}

RECENT CHAT (use only when the user is clarifying a prior reply — stay consistent with earlier numbers you gave):
{conversation_tail}

Rules:
- Respond ONLY in {language} (the user's language). If {language} is "en", respond in English.
- Lead with the most important insight or number.
- Use simple language — no jargon. Explain terms if needed.
- Portfolio totals (total invested, current value, XIRR, number of funds) MUST match PORTFOLIO_DB in USER FACTS if you mention them; if the Agent JSON matches PORTFOLIO_DB, use those values.
- Do not blend unrelated topics (e.g. do not mix FIRE corpus or goal-SIP numbers into a portfolio-holdings answer unless this turn's agent output is explicitly about FIRE/goals).
- If the user is asking what you meant, why, or to clarify the last answer, explain using USER FACTS + this turn's Agent output only — do not invent a new scenario.
- Include specific ₹ numbers from the data (don't round excessively).
- End with ONE clear, actionable step the user should take (or one clarification sentence if they only asked for meaning).
- Use ₹ for currency, not "Rs" or "INR".
{voice_instruction}

Agent used: {agent_used}
Agent output:
{agent_output}

User's original question: {message}

Your response (in {language}):"""

_SYNTH_SHORT = """You are CREDA. Summarize this financial agent output for the user in {language}.
Keep under {word_limit} words. Use ₹ for money. One clear next step at the end (or a direct clarification if they asked what something meant).

USER FACTS (database — do not contradict):
{user_facts}

RECENT CHAT:
{conversation_tail}

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
    *,
    user_facts: str = "",
    conversation_tail: str = "",
) -> str:
    """Convert raw agent output dict into user-facing natural language response."""
    compact_out = _compact_json(agent_output, 2800)
    word_limit = 120 if voice_mode else 200
    uf = (user_facts or "").strip() or "(none — treat agent JSON as sole source of numbers)"
    ct = (conversation_tail or "").strip() or "(none)"

    def _primary_prompt() -> str:
        return _SYNTH_PROMPT.format(
            language=language,
            voice_instruction=_VOICE_LINE if voice_mode else _TEXT_LINE,
            agent_used=agent_used,
            agent_output=compact_out,
            message=message or "",
            user_facts=uf,
            conversation_tail=ct,
        )

    def _fast_prompt() -> str:
        return _SYNTH_SHORT.format(
            language=language,
            word_limit=word_limit,
            agent_used=agent_used,
            data=compact_out,
            message=message or "",
            user_facts=uf,
            conversation_tail=ct,
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
