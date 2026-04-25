"""
LLM-based intent classifier — Tier 4 of the 4-tier cascade.

Only reached when keyword scoring AND embedding similarity are both uncertain.
Enhanced with hints from Tiers 2-3 to help the LLM disambiguate faster.
Uses fast_llm (llama-3.1-8b-instant) for speed (~1-2s).
"""
from typing import Optional
from app.core.llm import clip_prompt, fast_llm, invoke_llm
_VALID_INTENTS = {
    "dashboard", "portfolio", "portfolio_xray", "stress_test", "fire_planner", "money_health",
    "tax_wizard", "budget_coach", "goal_planner", "couples_finance",
    "sip_calculator", "rag_query", "general_chat",
    "market_pulse", "tax_copilot", "money_personality", "goal_simulator",
    "social_proof", "et_research", "human_handoff", "family_wealth",
    "expense_analytics",
}

_BASE_PROMPT = """Classify the user message into EXACTLY ONE intent. Respond with ONLY the intent name, nothing else.

Intents:
• dashboard → main app home / summary dashboard page (not portfolio holdings)
• portfolio → my portfolio page, mutual funds list, holdings page (not X-Ray, not tax)
• portfolio_xray → CAMS PDF, XIRR, fund overlap, expense ratio of funds, deep portfolio analysis
• stress_test → "what if" scenarios, life events impact, market crash simulation, Monte Carlo
• fire_planner → FIRE, early retirement, financial independence, corpus target, 4% rule
• money_health → health score, financial checkup, emergency fund, insurance coverage
• tax_wizard → tax regime, 80C/80D deductions, HRA, ITR, tax saving, ELSS, Form 16
• budget_coach → budget, spending, savings rate, 50/30/20 (not one-off purchase logging)
• expense_analytics → log/add/record a purchase or expense, spending breakdown, my expenses page, category totals
• goal_planner → goals, save for house/car/education, target amount, down payment
• couples_finance → couple, partner, spouse, joint finances, split expenses
• sip_calculator → SIP amount, step-up SIP, SIP returns calculator
• market_pulse → market news, Nifty, Sensex, today's market, FII/DII flows, bull/bear
• tax_copilot → year-round tax optimization, tax-loss harvesting, advance tax, tax deadlines
• money_personality → financial personality, investor type, risk profile assessment
• goal_simulator → what-if scenarios for goals, adjust SIP/returns, simulation sliders
• social_proof → peer comparison, how others invest, age group benchmarks
• et_research → deep research, explain concepts, articles, knowledge, detailed analysis
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

    parts.append(f"\nUser message: {clip_prompt(message, 1800)}")
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
        result = await invoke_llm(fast_llm, prompt)
        intent = result.content.strip().lower().replace(" ", "_").strip(".")
        return intent if intent in _VALID_INTENTS else "general_chat"
    except Exception:
        return "general_chat"
