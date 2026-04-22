"""
4-Tier Intent Classification Engine for CREDA.

Tier 1 — Follow-up detection       (0ms)  : conversational continuations → same agent
Tier 2 — Weighted keyword scoring   (0ms)  : multi-match disambiguation via specificity weights
Tier 3 — Embedding similarity       (~10ms): sentence-transformers/all-MiniLM-L6-v2 on CPU
Tier 4 — LLM classifier             (1-2s) : Groq llama-3.1-8b with embedding hints + context

Each tier is tried in order; first confident match wins.
Saves ~95% of LLM API calls compared to LLM-only classification.

Inspired by production cascading classifiers used in ChatGPT/Claude-style routing.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("creda.intent")


# ── Result dataclass ───────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Classification result with debug metadata."""
    intent: str
    confidence: float   # 0.0 → 1.0
    tier: int           # which tier resolved (1-4)
    tier_name: str      # human-readable: followup | keyword | embedding | llm
    latency_ms: float   # total classification time
    scores: dict = field(default_factory=dict)  # per-tier debug info


# ── Tier 1: Follow-up / Context Detection ──────────────────────────────

_FOLLOWUP_EXACT = re.compile(
    r"^\s*(yes|yeah|yep|ya|yea|ok|okay|sure|go ahead|continue|tell me more|more details"
    r"|explain more|elaborate|and\??|what about that|keep going|next|proceed|go on"
    r"|haan|accha|aur batao|aage|theek hai"
    r"|हाँ|हां|ठीक है|और बताओ|जारी रखो|आगे|विस्तार से"
    r"|ஆம்|சரி|தொடரவும்"
    r"|হ্যাঁ|ঠিক আছে|আরো বলো"
    r"|అవును|సరే|ఇంకా చెప్పండి"
    r"|ಹೌದು|ಸರಿ|ಮುಂದುವರಿಸಿ"
    r"|હા|ચાલુ રાખો"
    r")\s*[.!?]*\s*$",
    re.I,
)

_PRONOUN_CONTINUATION = re.compile(
    r"^\s*(what about|how about|and what|tell me about|more on|details on"
    r"|what's|whats|how's|hows)\s+(that|this|it|the same|those|them)",
    re.I,
)


def _detect_followup(message: str, last_intent: Optional[str]) -> Optional[str]:
    """Tier 1: detect conversational follow-ups → route to same agent."""
    if not last_intent or last_intent == "general_chat":
        return None
    msg = message.strip()
    if len(msg) > 80:  # real follow-ups are usually short
        return None
    if _FOLLOWUP_EXACT.match(msg) or _PRONOUN_CONTINUATION.match(msg):
        return last_intent
    return None


# ── Main Entry Point ───────────────────────────────────────────────────

async def classify_intent(
    message: str,
    last_intent: Optional[str] = None,
) -> IntentResult:
    """
    4-tier intent classification cascade.

    Args:
        message: raw user text (any language)
        last_intent: intent from the user's last turn (for follow-up detection)

    Returns:
        IntentResult with intent name, confidence, tier info, and debug scores.
    """
    t0 = time.monotonic()

    # ── Tier 1: Follow-up detection (0ms) ──
    intent = _detect_followup(message, last_intent)
    if intent:
        logger.debug("Tier 1 followup → %s (%.1fms)", intent, _ms(t0))
        return IntentResult(
            intent=intent, confidence=0.90, tier=1,
            tier_name="followup", latency_ms=_ms(t0),
        )

    # ── Tier 2: Weighted keyword scoring (0ms) ──
    from app.services.intent_classifier import keyword_score_classify
    matches = keyword_score_classify(message)
    if matches:
        top_intent, top_score = matches[0]
        second_score = matches[1][1] if len(matches) > 1 else 0.0
        gap = top_score - second_score

        # Confident if: score >= 3.0 (strong unique match) OR clear gap over 2nd place
        if top_score >= 3.0 or (top_score >= 1.5 and gap >= 1.0):
            logger.debug(
                "Tier 2 keyword → %s (score=%.1f, gap=%.1f, %.1fms)",
                top_intent, top_score, gap, _ms(t0),
            )
            return IntentResult(
                intent=top_intent,
                confidence=min(0.95, 0.70 + top_score * 0.05),
                tier=2, tier_name="keyword", latency_ms=_ms(t0),
                scores={"keyword_top3": [(i, round(s, 2)) for i, s in matches[:3]]},
            )

    # ── Tier 3: Embedding similarity (~10ms) ──
    try:
        from app.services.intent_embeddings import embedding_match
        emb_intent, emb_sim, top3 = embedding_match(message)
        if emb_intent and emb_sim >= 0.78:
            logger.debug(
                "Tier 3 embedding → %s (sim=%.3f, %.1fms)",
                emb_intent, emb_sim, _ms(t0),
            )
            return IntentResult(
                intent=emb_intent, confidence=emb_sim,
                tier=3, tier_name="embedding", latency_ms=_ms(t0),
                scores={"embedding_top3": top3},
            )
    except Exception as e:
        logger.warning("Tier 3 embedding skipped: %s", e)
        top3 = []

    # ── Tier 4: LLM classifier (1-2s, safety net) ──
    hints = top3[:2] if top3 else []
    keyword_hint = matches[0][0] if matches else None

    from app.agents.intent_router import llm_classify_intent
    intent = await llm_classify_intent(
        message, hints=hints, last_intent=last_intent, keyword_hint=keyword_hint,
    )
    logger.debug("Tier 4 LLM → %s (%.1fms)", intent, _ms(t0))
    return IntentResult(
        intent=intent, confidence=0.80,
        tier=4, tier_name="llm", latency_ms=_ms(t0),
        scores={
            "embedding_top3": top3 or [],
            "keyword_top3": [(i, round(s, 2)) for i, s in matches[:3]] if matches else [],
        },
    )


def _ms(t0: float) -> float:
    return round((time.monotonic() - t0) * 1000, 2)
