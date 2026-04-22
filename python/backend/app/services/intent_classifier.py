"""
Keyword pre-classifier — router-level gate, runs BEFORE LangGraph.

Saves a Groq API call for ~90% of queries by matching known keyword patterns.
Returns None when uncertain → caller falls through to LLM intent classifier.
"""
import re

# ── Keyword → intent mapping ──────────────────────────────────────────
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Portfolio X-Ray
    (re.compile(r"\b(cams|kfintech|mutual fund|portfolio|xirr|xray|x-ray|holdings|nav|sip return|fund overlap|expense ratio)\b", re.I), "portfolio_xray"),
    # Stress Test
    (re.compile(r"\b(stress test|what if|market crash|job loss|baby|marriage impact|life event|scenario|monte carlo)\b", re.I), "stress_test"),
    # FIRE Planner
    (re.compile(r"\b(fire|early retire|retirement|retire early|financial independence|fire number|corpus target|4% rule)\b", re.I), "fire_planner"),
    # Tax Wizard
    (re.compile(r"\b(tax|80c|80d|80ccd|hra|home loan interest|old regime|new regime|deduction|itr|form 16|tax saving|elss)\b", re.I), "tax_wizard"),
    # Money Health Score
    (re.compile(r"\b(health score|money health|financial health|financial score|credit score|emergency fund check|insurance check)\b", re.I), "money_health"),
    # Budget Coach
    (re.compile(r"\b(budget|spending|expense track|overspend|50.30.20|savings rate|cut cost|monthly budget)\b", re.I), "budget_coach"),
    # Goal Planner
    (re.compile(r"\b(goal|target amount|save for|house|car|education|wedding|down payment|goal plan)\b", re.I), "goal_planner"),
    # Couples Finance
    (re.compile(r"\b(couple|partner|spouse|joint|split|shared expense|combined income|marriage finance)\b", re.I), "couples_finance"),
    # SIP Calculator
    (re.compile(r"\b(sip calculator|sip amount|monthly sip|step.up sip|sip return|how much sip)\b", re.I), "sip_calculator"),
    # Market Pulse (NEW)
    (re.compile(r"\b(market|nifty|sensex|stock|bull|bear|correction|rally|fii|dii|market today|market news|market crash|index)\b", re.I), "market_pulse"),
    # Tax Copilot (NEW)
    (re.compile(r"\b(tax.?loss|harvest|tax copilot|advance tax|tax deadline|tax optimization|year.?round tax|tax planning)\b", re.I), "tax_copilot"),
    # Money Personality (NEW)
    (re.compile(r"\b(personality|money type|financial personality|risk profile|investor type|behavioural|behavioral|money mindset)\b", re.I), "money_personality"),
    # Goal Simulator (NEW)
    (re.compile(r"\b(simulat|what if.*sip|what if.*return|scenario model|goal simulator|drag.*slider|adjust.*sip)\b", re.I), "goal_simulator"),
    # Social Proof (NEW)
    (re.compile(r"\b(peer|people like me|others|crowd|benchmark|compare|how do i stack|age group|similar investor)\b", re.I), "social_proof"),
    # ET Research (NEW)
    (re.compile(r"\b(research|article|explain|what is|how does|guide|learn|knowledge|deep dive|detailed)\b", re.I), "et_research"),
    # Human Handoff (NEW)
    (re.compile(r"\b(talk to.*human|advisor|expert|help me|complex|confused|stressed|panicking|sebi|fraud|mis.?sell)\b", re.I), "human_handoff"),
    # Family Wealth (NEW)
    (re.compile(r"\b(family|household|spouse|parent|child|sibling|combined.*wealth|family.*net worth|household.*finance|family.*portfolio)\b", re.I), "family_wealth"),
    # RAG — regulations, general knowledge
    (re.compile(r"\b(rbi|sebi|ppf|nps|epf|atal pension|sukanya|pmjjby|pmsby|sgb|scss|government scheme|regulation)\b", re.I), "rag_query"),
]


def keyword_pre_classify(message: str) -> str | None:
    """
    Fast keyword matching — ~0ms, no LLM.
    Returns intent string or None if no confident match.
    """
    message = message.strip()
    if len(message) < 3:
        return None

    matched: list[str] = []
    for pattern, intent in _PATTERNS:
        if pattern.search(message):
            matched.append(intent)

    # Only return if exactly one intent matched (ambiguous → None → LLM fallback)
    if len(matched) == 1:
        return matched[0]

    return None
