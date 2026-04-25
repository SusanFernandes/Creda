"""
Deterministic voice navigation hints on top of model / keyword intent.

Fixes cases like "take me to the dashboard" being misrouted to portfolio because
generic 'portfolio' tokens appeared in the transcript or LLM guess.
"""
from __future__ import annotations

import re


def resolve_voice_page_intent(
    transcript: str,
    suggested: str,
    *,
    has_logged_expenses: bool,
) -> str:
    """Return final navigation intent for voice / URL mapping."""
    if has_logged_expenses:
        return "expense_analytics"

    t = (transcript or "").lower().strip()
    if not t:
        return suggested

    # Deep portfolio analysis / X-Ray (explicit technical ask)
    if re.search(r"\b(x-?ray|xirr|fund\s+overlap|overlap|cams|kfintech|expense\s+ratio)\b", t):
        return "portfolio_xray"

    # Main app dashboard — must not require the word "dashboard" only (home, main screen, etc.)
    dash_hit = re.search(
        r"\b(dashboard|main\s+screen|home\s+page|home\s+screen|main\s+page|"
        r"summary\s+page|overview\s+page|creda\s+home|open\s+home|go\s+home|"
        r"डैशबोर्ड|होम|मुख्य\s*पृष्ठ)\b",
        t,
    )
    port_hit = re.search(
        r"\b(my\s+portfolio|portfolio\s+page|the\s+portfolio\s+page|mutual\s+funds?\s+page|"
        r"holdings\s+page|funds?\s+list|show\s+my\s+funds|open\s+my\s+portfolio|"
        r"go\s+to\s+portfolio|navigate\s+to\s+portfolio|पोर्टफोलियो\s+पेज)\b",
        t,
    )
    if dash_hit and not port_hit:
        return "dashboard"
    if port_hit and not dash_hit:
        return "portfolio"
    # Both mentioned: first wins by order in utterance (simple)
    if dash_hit and port_hit:
        if dash_hit.start() <= port_hit.start():
            return "dashboard"
        return "portfolio"

    # Plain "portfolio" / "mutual funds" without dashboard — holdings page, not X-Ray
    if re.search(r"\b(mutual\s+funds?|my\s+funds|holdings)\b", t) and not re.search(
        r"\b(dashboard|main\s+screen|home\s+page)\b", t
    ):
        return "portfolio"

    return suggested
