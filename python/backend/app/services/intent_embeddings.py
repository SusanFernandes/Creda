"""
Tier 3 — Semantic embedding matcher using sentence-transformers/all-MiniLM-L6-v2.

At startup (lazy):  encode curated trigger phrases → compute per-intent centroids
At runtime:         encode user message → cosine similarity vs intent centroids (~10ms on CPU)

The 0.78 threshold is deliberately high to avoid false positives — uncertain
queries fall through to the LLM classifier (Tier 4).
"""
import logging
import os
import threading
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("creda.intent.embedding")

# Local model directory — downloaded once by `make init`, gitignored
# Resolves to python/models/all-MiniLM-L6-v2/
# parents: [0]=services, [1]=app, [2]=backend, [3]=python
_MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "all-MiniLM-L6-v2"

# ── Curated trigger phrases per intent ─────────────────────────────────
# Each list should have 6-12 natural-language examples that a user might say.
# Mix formal + informal + short + long so the centroid captures the concept.

_INTENT_TRIGGERS: dict[str, list[str]] = {
    "portfolio_xray": [
        "analyze my mutual fund portfolio",
        "upload CAMS statement",
        "what is my portfolio XIRR",
        "show fund overlap in my portfolio",
        "check my expense ratio",
        "review my mutual fund holdings",
        "portfolio analysis",
        "how are my investments doing",
        "my SIP returns percentage",
        "which funds should I exit",
        "portfolio health check",
    ],
    "stress_test": [
        "what happens if market crashes 30 percent",
        "stress test my portfolio",
        "what if I lose my job",
        "impact of baby on my finances",
        "marriage impact on my budget",
        "what if there is a recession",
        "scenario analysis for my portfolio",
        "run a Monte Carlo simulation",
        "how will a market downturn affect me",
    ],
    "fire_planner": [
        "when can I retire early",
        "calculate my FIRE number",
        "how much do I need for early retirement",
        "financial independence plan",
        "what is my corpus target for retirement",
        "4 percent rule calculation",
        "how many years to FIRE",
        "plan my early retirement",
        "when can I stop working",
    ],
    "tax_wizard": [
        "how to save tax under 80C",
        "old vs new tax regime comparison",
        "calculate my income tax",
        "HRA exemption calculation",
        "what tax deductions can I claim",
        "ELSS for tax saving",
        "file my ITR",
        "form 16 analysis",
        "how much tax do I owe this year",
        "tax saving investments",
    ],
    "money_health": [
        "check my financial health score",
        "how healthy are my finances",
        "do I have enough emergency fund",
        "insurance coverage check",
        "financial checkup",
        "rate my financial health",
        "am I financially healthy",
        "money health assessment",
    ],
    "budget_coach": [
        "help me create a budget",
        "I am overspending this month",
        "50 30 20 budget plan",
        "track my expenses",
        "where is my money going",
        "cut my expenses",
        "savings rate improvement",
        "monthly budget review",
        "how to spend less and save more",
    ],
    "goal_planner": [
        "plan for buying a house",
        "save for my child education",
        "wedding savings plan",
        "how much to save for a car",
        "goal based investment plan",
        "create a savings goal",
        "down payment calculator",
        "how to reach my financial goal",
        "save for a vacation abroad",
    ],
    "couples_finance": [
        "how to manage finances as a couple",
        "split expenses with my partner",
        "joint financial planning with spouse",
        "combined income management",
        "marriage finance planning",
        "should we have a joint account",
        "my partner's income and expenses",
    ],
    "sip_calculator": [
        "calculate SIP returns",
        "how much SIP for 1 crore",
        "step up SIP calculator",
        "monthly SIP amount needed",
        "SIP return projection",
        "what SIP amount do I need for my goal",
    ],
    "market_pulse": [
        "how is the market today",
        "Nifty 50 performance today",
        "Sensex update",
        "FII DII data today",
        "market news today",
        "is the market going up or down",
        "stock market update",
        "market rally or correction",
    ],
    "tax_copilot": [
        "year round tax optimization",
        "tax loss harvesting opportunity",
        "advance tax deadline this quarter",
        "quarterly tax planning",
        "optimize my taxes throughout the year",
        "tax planning calendar",
        "when to pay advance tax",
    ],
    "money_personality": [
        "what is my financial personality type",
        "assess my risk profile",
        "what kind of investor am I",
        "money behavior analysis",
        "my investing style",
        "am I a conservative or aggressive investor",
        "financial personality assessment",
    ],
    "goal_simulator": [
        "simulate goal with different SIP amounts",
        "what if I increase my SIP",
        "goal scenario modeling",
        "adjust return rate and see impact",
        "play with goal parameters",
        "how does changing my SIP affect my goal",
    ],
    "social_proof": [
        "how do I compare to others my age",
        "people like me savings benchmark",
        "peer comparison for investments",
        "am I saving enough compared to others",
        "how do similar investors perform",
        "age group financial benchmarks",
    ],
    "et_research": [
        "explain mutual fund types in detail",
        "what is a systematic withdrawal plan",
        "detailed guide on NPS",
        "research on index funds vs active funds",
        "deep dive into debt funds",
        "how will RBI rate cut affect my portfolio",
        "compare Nifty IT versus Nifty Bank over three years",
        "macro outlook for Indian equities this quarter",
        "FII flows and market implications",
        "sector rotation strategy for Indian markets",
    ],
    "life_event_advisor": [
        "I received a five lakh rupee bonus how should I invest it",
        "performance bonus allocation tax saving",
        "inheritance received what to do with the money",
        "new baby financial planning India",
        "got married need joint financial plan",
        "lost my job emergency fund advice",
        "bought a house down payment and EMI planning",
        "parents need financial support planning",
        "lump sum windfall deployment strategy",
    ],
    "expense_analytics": [
        "show my spending breakdown by category",
        "where does my salary go each month",
        "analyze my expenses and find waste",
        "category wise spending analysis",
        "expense analytics for my budget",
        "how much am I spending on dining out",
        "track my monthly spending patterns",
    ],
    "onboarding": [
        "I am new here help me set up my profile",
        "complete onboarding for Creda",
        "walk me through profile setup",
        "first time user financial questionnaire",
        "setup my profile step by step",
    ],
    "opportunity_radar": [
        "show insider buying alerts for stocks I follow",
        "bulk deals and block deals today NSE",
        "earnings surprise opportunities radar",
        "corporate filing alerts for my watchlist",
        "SEBI insider trading disclosures summary",
        "daily stock opportunity signals",
    ],
    "chart_pattern": [
        "find stocks with RSI divergence today",
        "chart pattern scanner for NSE stocks",
        "golden cross detection Indian equities",
        "breakout above fifty two week high",
        "technical pattern analysis for my watchlist",
        "MACD crossover stocks to watch",
    ],
    "human_handoff": [
        "I want to talk to a human advisor",
        "connect me to a financial expert",
        "this is too complex for a bot",
        "I am stressed about my finances",
        "report SEBI fraud",
        "mutual fund mis-selling complaint",
        "I need professional financial advice",
    ],
    "family_wealth": [
        "show my family combined wealth",
        "household net worth calculation",
        "add parent portfolio to family view",
        "family financial planning",
        "combined family investments",
        "spouse and my total portfolio",
        "family wealth dashboard",
    ],
    "rag_query": [
        "what are PPF interest rates",
        "NPS withdrawal rules",
        "SEBI regulations on mutual funds",
        "government savings schemes in India",
        "EPF withdrawal rules",
        "Atal Pension Yojana details",
        "Sukanya Samriddhi scheme benefits",
        "RBI guidelines on fixed deposits",
    ],
    "general_chat": [
        "hello",
        "hi there",
        "good morning",
        "how are you",
        "thank you for the help",
        "what can you do",
        "help me with my finances",
        "I have a question",
    ],
}


# ── Singleton: lazy-load model + precompute centroids ─────────────────

_lock = threading.Lock()
_model = None                       # SentenceTransformer instance
_centroids: dict[str, np.ndarray] = {}  # intent → centroid vector
_ready = False


def _ensure_loaded():
    """Lazy-load the model and build centroids on first call."""
    global _model, _centroids, _ready
    if _ready:
        return
    with _lock:
        if _ready:
            return
        try:
            from sentence_transformers import SentenceTransformer
            # Prefer local offline copy; fall back to HuggingFace Hub download
            if _MODEL_DIR.exists():
                logger.info("Loading MiniLM from local cache: %s", _MODEL_DIR)
                _model = SentenceTransformer(str(_MODEL_DIR))
            else:
                logger.info("Local model not found — downloading all-MiniLM-L6-v2 from HuggingFace...")
                _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
                # Save locally so next start is fully offline
                _MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
                _model.save(str(_MODEL_DIR))
                logger.info("Model saved to %s", _MODEL_DIR)

            for intent, phrases in _INTENT_TRIGGERS.items():
                vecs = _model.encode(phrases, normalize_embeddings=True)
                _centroids[intent] = np.mean(vecs, axis=0)
                # Normalize the centroid itself for fast cosine sim via dot product
                norm = np.linalg.norm(_centroids[intent])
                if norm > 0:
                    _centroids[intent] /= norm

            logger.info("Embedding centroids built for %d intents", len(_centroids))
            _ready = True
        except Exception as e:
            logger.warning("Embedding model failed to load: %s — Tier 3 disabled", e)
            _ready = True  # mark ready so we don't retry endlessly
            _model = None


def embedding_match(
    message: str,
    threshold: float = 0.78,
) -> tuple[Optional[str], float, list[tuple[str, float]]]:
    """
    Encode *message* and compare against pre-computed intent centroids.

    Returns:
        (best_intent | None, best_similarity, top_3_list)
        top_3_list: [(intent, similarity), ...] always returned for Tier 4 hints
    """
    _ensure_loaded()
    if _model is None or not _centroids:
        return None, 0.0, []

    try:
        vec = _model.encode([message], normalize_embeddings=True)[0]
        scores = {intent: float(np.dot(vec, centroid)) for intent, centroid in _centroids.items()}
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top3 = [(k, round(v, 4)) for k, v in ranked[:3]]

        best_intent, best_sim = ranked[0]
        if best_sim >= threshold:
            return best_intent, best_sim, top3
        return None, best_sim, top3
    except Exception as e:
        logger.warning("Embedding match failed: %s", e)
        return None, 0.0, []
