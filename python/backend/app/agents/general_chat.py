"""
General chat agent — fallback for greetings, casual conversation, unclassified intents.
"""
from typing import Any

from app.core.llm import fast_llm, invoke_llm
from app.agents.state import FinancialState

_GENERAL_PROMPT = """You are CREDA, a friendly AI financial coach for Indian users.
The user sent a casual or general message. Respond warmly and briefly.
If you can steer the conversation toward something financially useful, do so gently.

User message: {message}
Language: {language}

Rules:
- Respond in {language}
- Keep it under 100 words
- Be warm and friendly, like a trusted friend
- If appropriate, suggest a CREDA feature they could try (health score, portfolio xray, tax wizard, etc.)"""


async def run(state: FinancialState) -> dict[str, Any]:
    message = state.get("message", "")
    language = state.get("language", "en")

    try:
        result = await invoke_llm(
            fast_llm,
            _GENERAL_PROMPT.format(message=message, language=language),
        )
        return {"response_text": result.content.strip()}
    except Exception:
        return {"response_text": "Hi! I'm CREDA, your financial coach. How can I help you today?"}
