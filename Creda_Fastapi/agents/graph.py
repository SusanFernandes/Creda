"""
LangGraph Orchestration — builds and compiles the multi-agent financial graph.

Flow:
  Entry → intent_router → (conditional) → specialist_agent → synthesizer → END
"""

from __future__ import annotations
import logging
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from agents.state import FinancialState
from agents.intent_router import detect_intent
from agents.portfolio_xray_agent import portfolio_xray_agent
from agents.stress_test_agent import stress_test_agent
from agents.fire_planner_agent import fire_planner_agent
from agents.tax_wizard_agent import tax_wizard_agent
from agents.money_health_agent import money_health_score_agent
from agents.rag_agent import rag_agent

logger = logging.getLogger(__name__)

# ─── Routing Function ─────────────────────────────────────────────────────────

_INTENT_TO_NODE = {
    "portfolio_xray":     "portfolio_xray",
    "stress_test":        "stress_test",
    "fire_planner":       "fire_planner",
    "money_health_score": "money_health",
    "tax_wizard":         "tax_wizard",
    "sip_calculator":     "fire_planner",     # reuse FIRE maths for SIP projection
    "budget_coach":       "money_health",
    "insurance_check":    "money_health",
    "goal_planner":       "fire_planner",
    "rag_query":          "rag",
    "couples_planner":    "fire_planner",
    "general_chat":       "rag",
}


def route_to_agent(state: FinancialState) -> str:
    """Return the next node name based on the detected intent."""
    intent = state.get("intent", "general_chat")
    node = _INTENT_TO_NODE.get(intent, "rag")
    logger.info("Routing intent '%s' → node '%s'", intent, node)
    return node


# ─── Response Synthesizer ─────────────────────────────────────────────────────

_LANG_MAP = {
    "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "bn": "Bengali",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "ur": "Urdu",
}


def synthesize_response(state: FinancialState) -> dict:
    """Final node — merges all agent outputs into a single user-facing response."""
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.5)
    language = state.get("language", "en")
    outputs = state.get("agent_outputs", {})
    user_msg = state["messages"][-1].content

    data_summary = "\n".join(
        f"{key}: {str(val)[:600]}" for key, val in outputs.items()
    )

    lang_instruction = ""
    if language != "en" and language in _LANG_MAP:
        lang_instruction = f"\nIMPORTANT: Respond in {_LANG_MAP[language]}."

    prompt = f"""You are CREDA, a friendly AI financial coach for Indian users.{lang_instruction}

User asked: "{user_msg}"

Analysis results:
{data_summary}

Synthesise into a helpful, clear response.
- Lead with the most important insight
- Use simple language (avoid jargon)
- Include specific numbers from the analysis
- End with ONE clear action the user should take
- Keep under 150 words (voice-friendly)
- Use ₹ for currency"""

    try:
        response_text = llm.invoke(prompt).content
    except Exception as e:
        logger.error("Synthesiser LLM failed: %s", e)
        # Graceful fallback — return raw data summary
        response_text = data_summary[:500] if data_summary else "I'm sorry, I couldn't process that."

    return {
        "final_response": response_text,
        "response_data": outputs,
    }


# ─── Build Graph ──────────────────────────────────────────────────────────────

def build_financial_graph():
    """Construct and compile the LangGraph state machine."""
    graph = StateGraph(FinancialState)

    # Nodes
    graph.add_node("intent_router", detect_intent)
    graph.add_node("portfolio_xray", portfolio_xray_agent)
    graph.add_node("stress_test", stress_test_agent)
    graph.add_node("fire_planner", fire_planner_agent)
    graph.add_node("money_health", money_health_score_agent)
    graph.add_node("tax_wizard", tax_wizard_agent)
    graph.add_node("rag", rag_agent)
    graph.add_node("synthesizer", synthesize_response)

    # Entry
    graph.set_entry_point("intent_router")

    # Conditional routing from intent_router
    graph.add_conditional_edges(
        "intent_router",
        route_to_agent,
        {
            "portfolio_xray": "portfolio_xray",
            "stress_test": "stress_test",
            "fire_planner": "fire_planner",
            "money_health": "money_health",
            "tax_wizard": "tax_wizard",
            "rag": "rag",
        },
    )

    # All specialists → synthesizer → END
    for node in ("portfolio_xray", "stress_test", "fire_planner",
                 "money_health", "tax_wizard", "rag"):
        graph.add_edge(node, "synthesizer")

    graph.add_edge("synthesizer", END)

    return graph.compile()


# Singleton compiled graph — created once at import time
financial_graph = build_financial_graph()
