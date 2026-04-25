"""
Single fast Groq call: raw speech transcript → structured navigation + optional expenses.

Used by voice navigate and voice pipeline to avoid embedding tier + redundant LLM passes.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.llm import clip_prompt, fast_llm, invoke_llm

logger = logging.getLogger("creda.voice_command")

_NAV_INTENTS = frozenset({
    "dashboard", "portfolio", "portfolio_xray", "stress_test", "fire_planner", "money_health",
    "tax_wizard", "tax_copilot", "budget_coach", "expense_analytics",
    "goal_planner", "goal_simulator", "couples_finance", "sip_calculator",
    "market_pulse", "money_personality", "social_proof", "et_research",
    "rag_query", "human_handoff", "family_wealth", "general_chat",
})


def _extract_json_obj(text: str) -> Optional[dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t)
    try:
        out = json.loads(t)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}\s*$", t)
    if m:
        try:
            out = json.loads(m.group(0))
            return out if isinstance(out, dict) else None
        except json.JSONDecodeError:
            return None
    return None


@dataclass
class VoiceCommandParse:
    intent: str
    normalized_message: str
    expenses: list[dict[str, Any]] = field(default_factory=list)
    skip_agent: bool = False
    speak_brief: bool = False


def _coerce_expense(row: Any) -> Optional[dict[str, Any]]:
    if not isinstance(row, dict):
        return None
    cat = str(row.get("category") or row.get("cat") or "General").strip()[:100]
    try:
        amt = float(row.get("amount", 0))
    except (TypeError, ValueError):
        return None
    if amt <= 0:
        return None
    desc = str(row.get("description") or row.get("desc") or "")[:500]
    return {"category": cat, "amount": amt, "description": desc}


_SYSTEM = """You parse short voice transcripts for a personal finance app (CREDA, India).
Reply with ONE JSON object only, no markdown, no explanation.

Schema:
{
  "intent": "<one navigation intent from the allowed list>",
  "normalized_message": "<one concise English line: what the user wants>",
  "expenses": [ { "category": "<budget category e.g. Transport, Shopping, Healthcare, General>", "amount": <number>, "description": "<short>" } ],
  "skip_agent": <true|false>,
  "speak_brief": <true|false>
}

Rules:
- If the user only asks to log/add/record a purchase or expense with NO analysis question, set skip_agent true and fill expenses (amount in rupees as a number; infer category from item).
- If they ask how they are doing, trends, advice, or "why/how", set skip_agent false and expenses may be empty or filled if they also logged something.
- If unclear, intent general_chat and skip_agent false and expenses [].
- Amounts: "7.5 lakh" or "7 lakh 50 thousand" → 750000. "50k" → 50000.
- Set speak_brief true if they want a spoken summary of that page using their data (e.g. describe, explain, tell me about, what will I see, how am I on this page) — not for a bare "take me there" only.
- Navigation (no expenses in the same utterance): choose ONE intent that matches the page name they said:
  • dashboard → main CREDA home / summary (words: dashboard, home page, main screen, overview, go home)
  • portfolio → mutual fund holdings list page (words: my portfolio, portfolio page, mutual funds page, holdings page) — NOT the same as dashboard
  • portfolio_xray → deep analysis only (XIRR, fund overlap, CAMS statement, expense ratio of funds)

Allowed intent values (exactly one):
dashboard, portfolio, portfolio_xray, stress_test, fire_planner, money_health, tax_wizard, tax_copilot, budget_coach, expense_analytics, goal_planner, goal_simulator, couples_finance, sip_calculator, market_pulse, money_personality, social_proof, et_research, rag_query, human_handoff, family_wealth, general_chat
"""


async def parse_voice_command(
    transcript: str,
    last_intent: Optional[str] = None,
) -> Optional[VoiceCommandParse]:
    """
    Returns VoiceCommandParse on success, None if Groq unavailable or parse failed.
    """
    t = (transcript or "").strip()
    if not t:
        return None

    ctx = ""
    if last_intent and last_intent != "general_chat":
        ctx = f"\nPrevious screen intent hint: {last_intent}\n"

    prompt = (
        _SYSTEM
        + ctx
        + "Transcript:\n"
        + clip_prompt(t, 1200)
        + "\nJSON:"
    )

    try:
        # Tight cap: JSON only, no long prose — keeps latency and TPD usage low.
        parse_llm = fast_llm.bind(max_tokens=384, temperature=0)
        msg = await invoke_llm(parse_llm, prompt)
        raw = getattr(msg, "content", None) or str(msg)
        data = _extract_json_obj(raw)
        if not data:
            logger.warning("voice_command_parser: no JSON in model output")
            return None
    except Exception as e:
        logger.warning("voice_command_parser: Groq failed: %s", e)
        return None

    intent = str(data.get("intent") or "general_chat").strip().lower().replace(" ", "_")
    if intent not in _NAV_INTENTS:
        intent = "general_chat"

    norm = str(data.get("normalized_message") or t).strip()[:500]
    if not norm:
        norm = t

    exp_list: list[dict[str, Any]] = []
    for row in data.get("expenses") or []:
        coerced = _coerce_expense(row)
        if coerced:
            exp_list.append(coerced)

    skip = bool(data.get("skip_agent"))
    speak_brief = bool(data.get("speak_brief") or data.get("want_voice_brief"))
    if exp_list:
        intent = "expense_analytics"

    from app.services.voice_nav_intent import resolve_voice_page_intent

    intent = resolve_voice_page_intent(
        t, intent, has_logged_expenses=bool(exp_list),
    )

    return VoiceCommandParse(
        intent=intent,
        normalized_message=norm,
        expenses=exp_list,
        skip_agent=skip and bool(exp_list),
        speak_brief=speak_brief,
    )
