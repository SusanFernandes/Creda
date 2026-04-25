"""
Personalized voice line when the user asks to describe/explain a page while navigating.

Uses Groq (fast model) + user profile (and light portfolio/expense context) — max ~50 words for TTS.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import clip_prompt, fast_llm, invoke_llm
from app.models import Budget, Expense, Portfolio, PortfolioFund, UserProfile

logger = logging.getLogger("creda.voice_nav_brief")

_BRIEF_TRIGGER = re.compile(
    r"\b("
    r"describe|explains?|tell\s+me(\s+about)?|what\s+('?s|is)\s+this|summarize|summary\s+of|"
    r"overview\s+of|walk\s+me\s+through|what\s+('?s|is)\s+on|"
    r"how\s+am\s+i|what\s+do\s+you\s+think|"
    r"money\s+personality|personality\s+type|investor\s+type|"
    r"this\s+page|that\s+page|about\s+the\s+page|explain\s+the\s+page"
    r")\b",
    re.I,
)


def wants_personalized_nav_brief(transcript: str) -> bool:
    """True when user is asking for substance about the destination page, not only 'go there'."""
    t = (transcript or "").strip()
    if len(t) < 6:
        return False
    return bool(_BRIEF_TRIGGER.search(t))


def _lang_instruction(language: str) -> str:
    lc = (language or "en").lower()
    if lc.startswith("hi"):
        return "Write the entire reply in simple Hindi (Devanagari), natural spoken style."
    if lc.startswith("ta"):
        return "Write the entire reply in simple spoken Tamil."
    if lc.startswith("te"):
        return "Write the entire reply in simple spoken Telugu."
    if lc.startswith("bn"):
        return "Write the entire reply in simple spoken Bengali."
    if lc.startswith("mr"):
        return "Write the entire reply in simple spoken Marathi."
    return "Write the entire reply in clear English."


async def _load_context(
    db: AsyncSession,
    user_id: str,
    intent: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {"intent": intent}

    pr = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = pr.scalar_one_or_none()
    if profile:
        cols = {c.name: getattr(profile, c.name) for c in UserProfile.__table__.columns}
        for k in ("id", "user_id", "created_at", "updated_at"):
            cols.pop(k, None)
        out["profile"] = cols
    else:
        out["profile"] = None

    port = (
        await db.execute(
            select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.created_at.desc())
        )
    ).scalars().first()
    if port:
        fr = await db.execute(select(PortfolioFund).where(PortfolioFund.portfolio_id == port.id))
        n_funds = len(fr.scalars().all())
        out["portfolio"] = {
            "total_invested": float(port.total_invested or 0),
            "current_value": float(port.current_value or 0),
            "xirr": float(port.xirr or 0),
            "fund_count": int(n_funds),
        }
    else:
        out["portfolio"] = None

    if intent == "expense_analytics":
        month = date.today().strftime("%Y-%m")
        er = await db.execute(
            select(func.sum(Expense.amount)).where(
                Expense.user_id == user_id,
                func.to_char(Expense.expense_date, "YYYY-MM") == month,
            )
        )
        month_spend = float(er.scalar() or 0)
        out["expenses_month"] = {"month": month, "total_logged": month_spend}
        br = await db.execute(
            select(Budget).where(Budget.user_id == user_id, Budget.month == month)
        )
        out["budget_rows"] = len(br.scalars().all())

    return out


_PAGE_HINTS: dict[str, str] = {
    "dashboard": "Main app home: give one tight snapshot of their money picture (income vs spend, cushion, next best step if obvious).",
    "portfolio": "Mutual fund holdings list: reference value vs invested, number of funds, XIRR if non-zero.",
    "portfolio_xray": "Deep portfolio analysis: overlap, XIRR, expense ratio themes — only what numbers support.",
    "money_health": "Financial health: emergency fund vs expenses, insurance flags, surplus.",
    "money_personality": "Investor style: infer from risk_appetite, savings rate, employment, dependents — do not invent a quiz result label unless risk_appetite maps to a clear type.",
    "fire_planner": "FIRE angle: corpus target vs age if present; keep practical.",
    "tax_wizard": "Tax planning angle: regime-relevant hints from HRA, rent, 80C-style fields if present.",
    "tax_copilot": "Year-round tax optimization angle, one concrete angle from profile.",
    "budget_coach": "Budget discipline from income, expenses, savings.",
    "expense_analytics": "Spending this month vs profile monthly_expenses; mention logged categories if totals help.",
    "goal_planner": "Goals: FIRE targets or savings if in profile.",
    "market_pulse": "Market briefing tone without inventing live prices — relate to their risk level.",
    "general_chat": "General helpful line tied to their numbers, still about why the app is useful.",
}


async def generate_nav_voice_brief(
    db: AsyncSession,
    user_id: str,
    intent: str,
    page_label: str,
    user_transcript: str,
    language: str,
    *,
    expense_note: str = "",
) -> Optional[str]:
    """
    Returns spoken text (<= ~50 words) or None to fall back to generic ack.
    """
    ctx = await _load_context(db, user_id, intent)
    hint = _PAGE_HINTS.get(intent, _PAGE_HINTS["general_chat"])

    payload = {
        "page": page_label,
        "intent": intent,
        "focus": hint,
        "user_said": clip_prompt(user_transcript, 400),
        "facts": ctx,
    }
    if expense_note:
        payload["recent_action"] = expense_note

    sys = (
        "You are CREDA, an Indian personal finance copilot. The user is navigating by voice.\n"
        "Task: say ONE short spoken reply they will hear while the app opens the page.\n"
        "Rules: at most 50 words. No markdown, no bullet symbols, no lists. No disclaimers about being an AI.\n"
        "Use only numbers and facts from the JSON; if data is missing, give a generic but honest one-liner.\n"
        "Do not promise returns or regulated advice; stay practical.\n"
        + _lang_instruction(language)
    )
    user_block = json.dumps(payload, ensure_ascii=False, default=str)[:3500]

    try:
        llm = fast_llm.bind(max_tokens=140, temperature=0.35)
        msg = await invoke_llm(llm, sys + "\n\nContext JSON:\n" + user_block, clip=False)
        text = (getattr(msg, "content", None) or str(msg)).strip()
        text = re.sub(r"\s+", " ", text)
        # Hard cap ~50 words
        words = text.split()
        if len(words) > 52:
            text = " ".join(words[:52]) + "…"
        return text or None
    except Exception as e:
        logger.warning("nav voice brief failed: %s", e)
        return None
