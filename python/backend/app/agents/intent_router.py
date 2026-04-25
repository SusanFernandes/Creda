"""
LLM-based intent classifier — Tier 4 of the 4-tier cascade.

Only reached when keyword scoring AND embedding similarity are both uncertain.
Enhanced with hints from Tiers 2-3 to help the LLM disambiguate faster.
Uses fast_llm (llama-3.1-8b-instant) for speed (~1-2s).
"""
from typing import Optional
from app.core.llm import fast_llm

_VALID_INTENTS = {
    "portfolio_xray", "stress_test", "fire_planner", "money_health",
    "tax_wizard", "budget_coach", "goal_planner", "couples_finance",
    "sip_calculator", "rag_query", "general_chat",
    "market_pulse", "tax_copilot", "money_personality", "goal_simulator",
    "social_proof", "et_research", "human_handoff", "family_wealth",
    "life_event_advisor", "expense_analytics", "onboarding",
    "chart_pattern", "opportunity_radar",
}

_BASE_PROMPT = """Classify the user message into EXACTLY ONE intent. Respond with ONLY the intent name, nothing else.

Intents:
• portfolio_xray → CAMS PDF, mutual funds, XIRR, holdings, NAV, fund overlap, expense ratio
• stress_test → "what if" scenarios, life events impact, market crash simulation, Monte Carlo
• fire_planner → FIRE, early retirement, financial independence, corpus target, 4% rule
• money_health → health score, financial checkup, emergency fund, insurance coverage
• tax_wizard → tax regime, 80C/80D deductions, HRA, ITR, tax saving, ELSS, Form 16
• budget_coach → budget, spending, expenses, savings rate, 50/30/20
• goal_planner → goals, save for house/car/education, target amount, down payment
• couples_finance → couple, partner, spouse, joint finances, split expenses
• sip_calculator → SIP amount, step-up SIP, SIP returns calculator
• market_pulse → market news, Nifty, Sensex, today's market, FII/DII flows, bull/bear
• tax_copilot → year-round tax optimization, tax-loss harvesting, advance tax, tax deadlines
• money_personality → financial personality, investor type, risk profile assessment
• goal_simulator → what-if scenarios for goals, adjust SIP/returns, simulation sliders
• social_proof → peer comparison, how others invest, age group benchmarks
• et_research → deep research, macro/RBI/FII, portfolio impact of news, sector/index comparison, detailed analysis
• life_event_advisor → bonus, inheritance, marriage, baby, job loss, home purchase, parent dependency, windfall allocation
• expense_analytics → spending breakdown, category-wise expenses, where money goes, expense analysis
• onboarding → new user, setup profile, complete onboarding, first time here
• opportunity_radar → insider trades, bulk/block deals, earnings surprises, opportunity signals, filings
• chart_pattern → RSI divergence, MACD cross, golden cross, breakout, 52-week high, technical patterns
• human_handoff → talk to human, advisor, stressed, complex situation, SEBI complaint, fraud
• family_wealth → family finances, household wealth, spouse/parent/child portfolio, combined net worth
• rag_query → RBI/SEBI regulations, PPF/NPS/EPF rules, government schemes, Sukanya/PMJJBY
• general_chat → greeting, casual, doesn't fit above"""


def _build_prompt(
    message: str,
    hints: list[tuple[str, float]] | None = None,
    last_intent: Optional[str] = None,
    keyword_hint: Optional[str] = None,
) -> str:
    """Build an enriched prompt with disambiguation hints."""
    parts = [_BASE_PROMPT]

    # Add context hints to help LLM disambiguate
    context_lines = []
    if keyword_hint:
        context_lines.append(f"Keyword analysis suggests: {keyword_hint}")
    if hints:
        hint_strs = [f"{name} (similarity={sim:.2f})" for name, sim in hints]
        context_lines.append(f"Semantic similarity suggests: {', '.join(hint_strs)}")
    if last_intent and last_intent != "general_chat":
        context_lines.append(f"Previous turn used: {last_intent}")

    if context_lines:
        parts.append("\nContext (use as hints, not absolute):\n" + "\n".join(f"• {l}" for l in context_lines))

    parts.append(f"\nUser message: {message}")
    parts.append("Intent:")
    return "\n".join(parts)


async def llm_classify_intent(
    message: str,
    hints: list[tuple[str, float]] | None = None,
    last_intent: Optional[str] = None,
    keyword_hint: Optional[str] = None,
) -> str:
    """Classify intent using LLM (Tier 4). Returns intent string."""
    try:
        prompt = _build_prompt(message, hints, last_intent, keyword_hint)
        result = await fast_llm.ainvoke(prompt)
        intent = result.content.strip().lower().replace(" ", "_").strip(".")
        return intent if intent in _VALID_INTENTS else "general_chat"
    except Exception:
        return "general_chat"
