"""
LLM-based intent classifier — fallback when keyword pre-classifier returns None.
Uses fast_llm (llama-3.1-8b-instant) for speed.
"""
from app.core.llm import fast_llm

_INTENT_PROMPT = """Classify the user message into EXACTLY ONE intent. Respond with ONLY the intent name, nothing else.

Intents:
• portfolio_xray → CAMS PDF, mutual funds, XIRR, holdings, NAV, fund overlap, expense ratio
• stress_test → "what if" scenarios, life events impact, market crash simulation
• fire_planner → FIRE, early retirement, financial independence, corpus target
• money_health → health score, financial checkup, emergency fund, insurance coverage
• tax_wizard → tax regime, 80C/80D deductions, HRA, ITR, tax saving, ELSS
• budget_coach → budget, spending, expenses, savings rate, 50/30/20
• goal_planner → goals, save for house/car/education, target amount
• couples_finance → couple, partner, spouse, joint finances, split expenses
• sip_calculator → SIP amount, step-up SIP, SIP returns
• market_pulse → market news, Nifty, Sensex, today's market, FII/DII flows
• tax_copilot → year-round tax optimization, tax-loss harvesting, advance tax, tax deadlines
• money_personality → financial personality, investor type, risk profile assessment
• goal_simulator → what-if scenarios for goals, adjust SIP/returns, simulation
• social_proof → peer comparison, how others invest, age group benchmarks
• et_research → deep research, explain concepts, articles, knowledge, detailed analysis
• human_handoff → talk to human, advisor, stressed, complex situation, SEBI complaint
• family_wealth → family finances, household wealth, spouse/parent/child portfolio, combined net worth
• rag_query → RBI/SEBI regulations, PPF/NPS/EPF rules, government schemes
• general_chat → greeting, casual, doesn't fit above

User message: {message}
Intent:"""


async def llm_classify_intent(message: str) -> str:
    """Classify intent using LLM. Returns intent string."""
    try:
        result = await fast_llm.ainvoke(_INTENT_PROMPT.format(message=message))
        intent = result.content.strip().lower().replace(" ", "_")
        valid = {
            "portfolio_xray", "stress_test", "fire_planner", "money_health",
            "tax_wizard", "budget_coach", "goal_planner", "couples_finance",
            "sip_calculator", "rag_query", "general_chat",
            "market_pulse", "tax_copilot", "money_personality", "goal_simulator",
            "social_proof", "et_research", "human_handoff", "family_wealth",
        }
        return intent if intent in valid else "general_chat"
    except Exception:
        return "general_chat"
