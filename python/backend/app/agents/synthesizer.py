"""
Synthesizer node — converts raw agent output (dicts/numbers) into natural language.
This is the MOST important node: it's what the user actually reads/hears.

Includes language instruction and voice-mode word limit.
"""
from app.core.llm import primary_llm

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

_VOICE_LINE = "- Keep under 200 words (this is a voice response — short and clear)."
_TEXT_LINE = "- Keep under 300 words."


async def synthesize(
    agent_output: dict,
    agent_used: str,
    message: str,
    language: str = "en",
    voice_mode: bool = False,
) -> str:
    """Convert raw agent output dict into user-facing natural language response."""
    if agent_output.get("status") == "PROFILE_INCOMPLETE":
        return agent_output.get("message") or ""

    prompt = _SYNTH_PROMPT.format(
        language=language,
        voice_instruction=_VOICE_LINE if voice_mode else _TEXT_LINE,
        agent_used=agent_used,
        agent_output=str(agent_output),
        message=message,
    )
    result = await primary_llm.ainvoke(prompt)
    return result.content.strip()
