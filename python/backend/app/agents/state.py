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
    # One-line-per-field snapshot from DB for the synthesizer (must not contradict agent JSON)
    user_facts: Optional[str]
    real_expenses: Optional[dict]      # category → total amount (from DB)
    budget_data: Optional[dict]        # category → {planned, actual}

    # ── Stress test: explicit event keys from UI (not parsed from message) ──
    stress_event_keys: Optional[list[str]]

    # ── Goal planner: DB-backed goals ──
    stored_goals: Optional[list[dict]]

    # ── Misc (DB session for agents that need it) ──
    db: Optional[Any]

    # ── Agent outputs (each agent writes its key) ──
    agent_outputs: dict[str, Any]
    agent_used: str

    # ── Final ──
    response: str
