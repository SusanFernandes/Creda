"""
LangGraph state schema for CREDA financial agents.
"""
from typing import Any, Optional
from typing_extensions import TypedDict


class FinancialState(TypedDict, total=False):
    # ── Input ──
    user_id: str
    message: str
    intent: str
    language: str
    voice_mode: bool
    history: list[dict]

    # ── Profile (loaded by graph) ──
    user_profile: Optional[dict]
    portfolio_data: Optional[dict]
    real_expenses: Optional[dict]      # category → total amount (from DB)
    budget_data: Optional[dict]        # category → {planned, actual}

    # ── Misc (DB session for agents that need it) ──
    db: Optional[Any]

    # ── Agent outputs (each agent writes its key) ──
    agent_outputs: dict[str, Any]
    agent_used: str

    # ── Final ──
    response: str
