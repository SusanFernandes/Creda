"""
LangGraph orchestration — routes intent to the correct agent, then synthesizes.

Graph:
  load_profile → agent_node (conditional on intent) → synthesizer → END
"""
import logging
from typing import Any, AsyncIterator, Optional

from langgraph.graph import StateGraph, END
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import FinancialState
from app.agents.synthesizer import synthesize

logger = logging.getLogger("creda.graph")


# ── Node: load user profile from DB ──────────────────────────────────

async def load_profile_node(state: FinancialState) -> dict:
    """Lazy-import to avoid circular deps. Load profile + portfolio from DB."""
    from app.database import AsyncSessionLocal
    from app.models import UserProfile, Portfolio, PortfolioFund

    async with AsyncSessionLocal() as db:
        # Profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == state["user_id"])
        )
        profile = result.scalar_one_or_none()
        profile_dict = None
        if profile:
            profile_dict = {c.name: getattr(profile, c.name) for c in UserProfile.__table__.columns}

        # Portfolio
        port_result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == state["user_id"]).order_by(Portfolio.created_at.desc())
        )
        portfolio = port_result.scalar_one_or_none()
        portfolio_dict = None
        if portfolio:
            funds_result = await db.execute(
                select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
            )
            funds = funds_result.scalars().all()
            portfolio_dict = {
                "total_invested": portfolio.total_invested,
                "current_value": portfolio.current_value,
                "xirr": portfolio.xirr,
                "funds": [
                    {c.name: getattr(f, c.name) for c in PortfolioFund.__table__.columns}
                    for f in funds
                ],
            }

        out: dict = {"user_profile": profile_dict, "portfolio_data": portfolio_dict}
        if state.get("intent") == "expense_analytics":
            from datetime import date as date_cls

            from app.models import Budget, Expense

            month = date_cls.today().strftime("%Y-%m")
            er = await db.execute(
                select(Expense.category, func.sum(Expense.amount)).where(
                    Expense.user_id == state["user_id"],
                    func.to_char(Expense.expense_date, "YYYY-MM") == month,
                ).group_by(Expense.category)
            )
            out["real_expenses"] = {c: float(a) for c, a in er.all()}
            br = await db.execute(
                select(Budget).where(
                    Budget.user_id == state["user_id"],
                    Budget.month == month,
                )
            )
            out["budget_data"] = {
                b.category: {"planned": float(b.planned_amount), "actual": float(b.actual_amount or 0)}
                for b in br.scalars().all()
            }
        return out


# ── Node: run the selected agent ──────────────────────────────────────

_AGENT_MAP = {
    "dashboard": "app.agents.general_chat",
    "portfolio": "app.agents.portfolio_xray",
    "portfolio_xray": "app.agents.portfolio_xray",
    "stress_test": "app.agents.stress_test",
    "fire_planner": "app.agents.fire_planner",
    "tax_wizard": "app.agents.tax_wizard",
    "money_health": "app.agents.money_health",
    "budget_coach": "app.agents.budget_coach",
    "expense_analytics": "app.agents.expense_analytics",
    "goal_planner": "app.agents.goal_planner",
    "couples_finance": "app.agents.couples_finance",
    "sip_calculator": "app.agents.sip_calculator",
    "rag_query": "app.agents.rag_agent",
    "onboarding": "app.agents.onboarding",
    "general_chat": "app.agents.general_chat",
    # ET-inspired agents
    "market_pulse": "app.agents.market_pulse",
    "tax_copilot": "app.agents.tax_copilot",
    "money_personality": "app.agents.money_personality",
    "goal_simulator": "app.agents.goal_simulator",
    "social_proof": "app.agents.social_proof",
    "et_research": "app.agents.et_research",
    "human_handoff": "app.agents.human_handoff",
    "family_wealth": "app.agents.family_wealth",
}


async def agent_node(state: FinancialState) -> dict:
    """Dynamically dispatch to the correct agent based on intent."""
    intent = state.get("intent", "general_chat")
    module_path = _AGENT_MAP.get(intent, "app.agents.general_chat")

    try:
        import importlib
        mod = importlib.import_module(module_path)
        agent_fn = getattr(mod, "run")
        output = await agent_fn(state)
    except Exception as e:
        logger.error("Agent %s failed: %s", intent, e, exc_info=True)
        output = {"error": str(e)}

    return {"agent_outputs": {intent: output}, "agent_used": intent}


# ── Node: synthesizer ────────────────────────────────────────────────

async def synthesizer_node(state: FinancialState) -> dict:
    """Convert raw agent output into natural language response."""
    agent_used = state.get("agent_used", "general_chat")
    outputs = state.get("agent_outputs", {})
    agent_output = outputs.get(agent_used, {})

    response = await synthesize(
        agent_output=agent_output,
        agent_used=agent_used,
        message=state.get("message", ""),
        language=state.get("language", "en"),
        voice_mode=state.get("voice_mode", False),
    )
    return {"response": response}


# ── Build the graph ───────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(FinancialState)
    g.add_node("load_profile", load_profile_node)
    g.add_node("agent", agent_node)
    g.add_node("synthesizer", synthesizer_node)

    g.set_entry_point("load_profile")
    g.add_edge("load_profile", "agent")
    g.add_edge("agent", "synthesizer")
    g.add_edge("synthesizer", END)

    return g


_compiled = _build_graph().compile()


# ── Public API ────────────────────────────────────────────────────────

async def run_agent(
    user_id: str,
    message: str,
    intent: str,
    language: str = "en",
    voice_mode: bool = False,
    history: list[dict] | None = None,
) -> dict:
    """Run the full LangGraph pipeline and return result dict."""
    initial_state: FinancialState = {
        "user_id": user_id,
        "message": message,
        "intent": intent,
        "language": language,
        "voice_mode": voice_mode,
        "history": history or [],
        "agent_outputs": {},
    }
    result = await _compiled.ainvoke(initial_state)
    return {
        "response": result.get("response", ""),
        "agent_used": result.get("agent_used", intent),
        "agent_outputs": result.get("agent_outputs", {}),
    }


async def run_agent_stream(
    user_id: str,
    message: str,
    intent: str,
    language: str = "en",
    voice_mode: bool = False,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    """Stream LangGraph execution — yields intermediate chunks for SSE."""
    initial_state: FinancialState = {
        "user_id": user_id,
        "message": message,
        "intent": intent,
        "language": language,
        "voice_mode": voice_mode,
        "history": history or [],
        "agent_outputs": {},
    }
    async for event in _compiled.astream(initial_state):
        # Each event is a dict with the node name as key
        for node_name, node_output in event.items():
            if "response" in node_output:
                yield node_output["response"]
