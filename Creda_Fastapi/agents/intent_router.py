"""
Intent Router Agent — classifies user messages and decides which specialist agent handles the request.
"""

from __future__ import annotations
import logging
from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)

INTENTS = [
    "portfolio_xray",
    "stress_test",
    "fire_planner",
    "money_health_score",
    "tax_wizard",
    "sip_calculator",
    "budget_coach",
    "insurance_check",
    "goal_planner",
    "rag_query",
    "couples_planner",
    "general_chat",
]

_SYSTEM_PROMPT = f"""You are a financial intent classifier for Indian users.
Classify the user message into EXACTLY one intent from the list below.

Intents:
{chr(10).join(f'- {i}' for i in INTENTS)}

Rules:
- If the user mentions CAMS, PDF, portfolio upload, mutual fund analysis, XIRR, fund overlap, or expense ratio → portfolio_xray
- If the user mentions "what if", crash, baby, marriage, job loss, life event → stress_test
- If the user mentions FIRE, early retirement, retirement corpus, retirement roadmap → fire_planner
- If the user mentions health score, financial health, how am I doing → money_health_score
- If the user mentions tax, old regime, new regime, 80C, deductions, HRA → tax_wizard
- If the user mentions SIP, monthly investment, compound, wealth calculator → sip_calculator
- If the user mentions budget, spending, needs wants savings, 50/30/20 → budget_coach
- If the user mentions insurance, term plan, health cover, LIC → insurance_check
- If the user mentions goal, save for, education, house, car, wedding → goal_planner
- If the user mentions couples, joint, husband wife, partner → couples_planner
- If the user asks about regulations, RBI, SEBI, government schemes, general finance → rag_query
- Anything else → general_chat

Respond with ONLY the intent name. No explanation, no quotes."""


def detect_intent(state: FinancialState) -> dict:
    """Detect intent from the last user message and return updated state."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    last_message = state["messages"][-1].content

    try:
        response = llm.invoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": last_message},
        ])
        detected = response.content.strip().lower().replace('"', "").replace("'", "")
        # Validate against known intents
        if detected not in INTENTS:
            logger.warning("Unknown intent '%s', falling back to general_chat", detected)
            detected = "general_chat"
    except Exception as e:
        logger.error("Intent detection failed: %s", e)
        detected = "general_chat"

    logger.info("Detected intent: %s for message: %.80s", detected, last_message)
    return {"intent": detected}
