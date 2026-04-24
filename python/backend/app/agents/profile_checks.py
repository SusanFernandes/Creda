"""Per-agent profile completeness (Part 1.2) — used when run() is invoked outside LangGraph."""

from __future__ import annotations

from typing import Any

from app.agents.state import FinancialState
from app.core.profile_guard import SKIP_PROFILE_GUARD, guard_for_intent


def profile_incomplete_payload(guard: dict[str, Any]) -> dict[str, Any]:
    missing = guard.get("missing") or []
    label = missing[0].replace("_", " ") if missing else "details"
    return {
        "status": "PROFILE_INCOMPLETE",
        "missing_fields": missing,
        "message": (
            "I need a bit more info to help you accurately. "
            f"Could you tell me your {label}?"
        ),
        "completeness_pct": guard.get("completeness_pct", 0),
        "data_quality": "partial",
    }


def require_complete_profile(state: FinancialState) -> dict[str, Any] | None:
    """Return PROFILE_INCOMPLETE dict or None if profile satisfies intent guard."""
    intent = state.get("intent", "general_chat")
    if intent in SKIP_PROFILE_GUARD:
        return None
    g = guard_for_intent(intent, state.get("user_profile"))
    if g["is_complete"]:
        return None
    return profile_incomplete_payload(g)
