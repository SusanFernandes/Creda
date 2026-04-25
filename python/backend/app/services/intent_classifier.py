"""
Keyword pre-classifier — Tier 2 of the 4-tier intent cascade.

Weighted keyword scoring with specificity disambiguation.
Each keyword group has a weight reflecting how uniquely it identifies an intent:
  3.0 = unique identifier — only one intent can have this term
  2.0 = strong signal — almost always means this intent
  1.0 = weak signal — could mean this intent or something generic

When multiple intents match, highest total score wins (if gap is clear).
Supports English + Hindi + Tamil + Telugu + Bengali + Marathi + Kannada + Gujarati.
"""
import re
from collections import defaultdict

# ── (pattern, intent, weight) tuples ───────────────────────────────────
# Each row: a compiled regex matching one or more terms, the intent it maps to,
# and how strongly those terms indicate that specific intent.

_WEIGHTED_RULES: list[tuple[re.Pattern, str, float]] = [
    # ── Portfolio X-Ray ──
    (re.compile(r"\b(cams|kfintech|xirr|x-?ray|fund.?overlap|expense.?ratio)\b", re.I), "portfolio_xray", 3.0),
    (re.compile(r"\b(mutual.?fund|portfolio|holdings|nav|sip.?return)\b", re.I), "portfolio_xray", 1.5),
    (re.compile(r"\b(पोर्टफोलियो|म्यूचुअल.?फंड|म्युचुअल|निवेश|ம்யூசுவல்|போர்ட்ஃபோலியோ|পোর্টফোলিও|মিউচুয়াল|పోర్ట్‌ఫోలియో|మ్యూచువల్|ಮ್ಯೂಚುಯಲ್|पोर्टफोलिओ)\b", re.I), "portfolio_xray", 1.5),

    # ── Stress Test (avoid generic "life event" — routes to life_event_advisor) ──
    (re.compile(r"\b(stress.?test|monte.?carlo)\b", re.I), "stress_test", 3.0),
    (re.compile(r"\b(market.?crash|job.?loss|recession|what.?if.+lose.?my.?job)\b", re.I), "stress_test", 2.5),
    (re.compile(r"\b(portfolio.?scenario|financial.?scenario|crash.?simulation)\b", re.I), "stress_test", 2.0),
    (re.compile(r"\b(तनाव.?परीक्षण|नौकरी.?छूट|बाजार.?गिरावट)\b", re.I), "stress_test", 2.0),

    # ── Life Event Advisor ──
    (re.compile(r"\b(bonus|performance.?bonus|variable.?pay|windfall|inheritance|inherited)\b", re.I), "life_event_advisor", 3.0),
    (re.compile(r"\b(new.?baby|baby.?born|pregnancy|got.?married|marriage|job.?loss|laid.?off|lost.?my.?job)\b", re.I), "life_event_advisor", 2.8),
    (re.compile(r"\b(home.?purchase|bought.?a.?house|property.?purchase|parent.?depend|elder.?care)\b", re.I), "life_event_advisor", 2.5),
    (re.compile(r"\b(life.?event.?advisor|life.?event.?money|lump.?sum.?received)\b", re.I), "life_event_advisor", 3.0),

    # ── Expense Analytics ──
    (re.compile(r"\b(expense.?analytics|spending.?breakdown|category.?wise.?spending|where(.?does)?.?my.?money)\b", re.I), "expense_analytics", 3.0),
    (re.compile(r"\b(spending.?analysis|spending.?by.?category|analyze.?my.?expenses|expense.?categories)\b", re.I), "expense_analytics", 2.5),

    # ── Onboarding ──
    (re.compile(r"\b(onboarding|setup.?my.?profile|complete.?my.?profile|new.?to.?creda|first.?time.?here)\b", re.I), "onboarding", 3.0),
    (re.compile(r"\b(fill.?profile|profile.?wizard|start.?onboarding)\b", re.I), "onboarding", 2.5),

    # ── PS6: Opportunity Radar ──
    (re.compile(r"\b(opportunity.?radar|bulk.?deal|block.?deal|insider.?buy|insider.?trading|earnings.?surprise)\b", re.I), "opportunity_radar", 3.0),
    (re.compile(r"\b(corporate.?filing|nse.?announcement|stock.?signals|deal.?alert)\b", re.I), "opportunity_radar", 2.0),

    # ── PS6: Chart Pattern Intelligence ──
    (re.compile(r"\b(chart.?pattern|technical.?pattern|candlestick.?pattern|rsi.?divergence|macd.?cross|golden.?cross|death.?cross)\b", re.I), "chart_pattern", 3.0),
    (re.compile(r"\b(52.?week.?high|breakout|support.?and.?resistance|double.?top|head.?and.?shoulders)\b", re.I), "chart_pattern", 2.5),

    # ── FIRE Planner ──
    (re.compile(r"\b(fire.?number|fire.?plan|4%.?rule|corpus.?target)\b", re.I), "fire_planner", 3.0),
    (re.compile(r"\b(fire|early.?retire|retire.?early|financial.?independence)\b", re.I), "fire_planner", 2.5),
    (re.compile(r"\b(retirement)\b", re.I), "fire_planner", 1.5),
    (re.compile(r"\b(रिटायरमेंट|सेवानिवृत्ति|जल्दी.?रिटायर|ஓய்வு|రిటైర్మెంట్|অবসর|निवृत्ती)\b", re.I), "fire_planner", 2.0),

    # ── Tax Wizard ──
    (re.compile(r"\b(80c|80d|80ccd|old.?regime|new.?regime|form.?16|elss)\b", re.I), "tax_wizard", 3.0),
    (re.compile(r"\b(hra|home.?loan.?interest|deduction|itr|tax.?saving)\b", re.I), "tax_wizard", 2.0),
    (re.compile(r"\b(tax)\b", re.I), "tax_wizard", 1.5),
    (re.compile(r"\b(टैक्स|कर.?बचत|कर.?कटौती|आयकर|வரி|పన్ను|কর|कर)\b", re.I), "tax_wizard", 2.0),
    (re.compile(r"(tax.?ka|mera.?tax|mere.?tax|tax.?status|tax.?kitna|tax.?kaise)\b", re.I), "tax_wizard", 3.0),

    # ── Money Health Score ──
    (re.compile(r"\b(health.?score|money.?health|financial.?health|financial.?score)\b", re.I), "money_health", 3.0),
    (re.compile(r"\b(credit.?score|emergency.?fund.?check|insurance.?check)\b", re.I), "money_health", 2.5),
    (re.compile(r"\b(वित्तीय.?स्वास्थ्य|आपातकालीन.?फंड|பணம்.?ஆரோக்கியம்|আর্থিক.?স্বাস্থ্য)\b", re.I), "money_health", 2.0),

    # ── Budget Coach ──
    (re.compile(r"\b(50.?30.?20|monthly.?budget|savings.?rate|expense.?track)\b", re.I), "budget_coach", 3.0),
    (re.compile(r"\b(budget|overspend|cut.?cost)\b", re.I), "budget_coach", 2.0),
    (re.compile(r"\b(spending|expense)\b", re.I), "budget_coach", 1.0),
    (re.compile(r"\b(बजट|खर्च|बचत|বাজেট|খরচ|వెచ్చం)\b", re.I), "budget_coach", 1.5),

    # ── Goal Planner ──
    (re.compile(r"\b(down.?payment|goal.?plan|target.?amount|save.?for)\b", re.I), "goal_planner", 3.0),
    (re.compile(r"\b(goal|education|wedding)\b", re.I), "goal_planner", 1.5),
    (re.compile(r"\b(house|car)\b", re.I), "goal_planner", 1.0),
    (re.compile(r"\b(लक्ष्य|बच्चों.?की.?शिक्षा|இலக்கு|கல்வி|লক্ষ্য|ध्येय|ಗುರಿ|లక్ష్యం)\b", re.I), "goal_planner", 1.5),

    # ── Couples Finance ──
    (re.compile(r"\b(couple|joint.?finance|shared.?expense|marriage.?finance|combined.?income)\b", re.I), "couples_finance", 3.0),
    (re.compile(r"\b(partner|spouse|split)\b", re.I), "couples_finance", 1.5),
    (re.compile(r"\b(पति|पत्नी|जोड़ा|साझा.?खर्च|கணவன்|மனைவி|দম্পতি|జంట|दांपत्य)\b", re.I), "couples_finance", 2.0),

    # ── SIP Calculator ──
    (re.compile(r"\b(sip.?calculator|step.?up.?sip|how.?much.?sip)\b", re.I), "sip_calculator", 3.0),
    (re.compile(r"\b(sip.?amount|monthly.?sip|sip.?return)\b", re.I), "sip_calculator", 2.0),
    (re.compile(r"\b(एसआईपी|सिप|எஸ்ஐபி|ఎస్.?ఐపీ|এসআইপি)\b", re.I), "sip_calculator", 2.0),

    # ── Market Pulse ──
    (re.compile(r"\b(nifty|sensex|fii|dii|market.?today|market.?news)\b", re.I), "market_pulse", 3.0),
    (re.compile(r"\b(bull|bear|correction|rally|stock|index)\b", re.I), "market_pulse", 2.0),
    (re.compile(r"\b(market)\b", re.I), "market_pulse", 1.0),
    (re.compile(r"\b(बाजार|शेयर|निफ्टी|सेंसेक्स|சந்தை|நிஃப்டி|বাজার|మార్కెట్|ಮಾರುಕಟ್ಟೆ)\b", re.I), "market_pulse", 1.5),

    # ── Tax Copilot ──
    (re.compile(r"\b(tax.?loss|harvest|tax.?copilot|tax.?deadline|year.?round.?tax)\b", re.I), "tax_copilot", 3.0),
    (re.compile(r"\b(advance.?tax|tax.?optimization|tax.?planning)\b", re.I), "tax_copilot", 2.0),
    (re.compile(r"\b(अग्रिम.?कर|कर.?नियोजन|வரி.?திட்டமிடல்|অগ্রিম.?কর)\b", re.I), "tax_copilot", 2.0),

    # ── Money Personality ──
    (re.compile(r"\b(money.?personality|financial.?personality|investor.?type|money.?type|money.?mindset)\b", re.I), "money_personality", 3.0),
    (re.compile(r"\b(personality|risk.?profile|behavioural|behavioral)\b", re.I), "money_personality", 2.0),
    (re.compile(r"\b(व्यक्तित्व|निवेशक.?प्रकार|ஆளுமை|ব্যক্তিত্ব|వ్యక్తిత్వం)\b", re.I), "money_personality", 2.0),

    # ── Goal Simulator ──
    (re.compile(r"\b(goal.?simulator|scenario.?model|drag.?slider|adjust.?sip)\b", re.I), "goal_simulator", 3.0),
    (re.compile(r"\b(simulat|what.?if.+sip|what.?if.+return)\b", re.I), "goal_simulator", 2.0),
    (re.compile(r"\b(सिमुलेशन|அனுகரிப்பு|সিমুলেশন)\b", re.I), "goal_simulator", 2.0),

    # ── Social Proof ──
    (re.compile(r"\b(people.?like.?me|how.?do.?i.?stack|similar.?investor|age.?group)\b", re.I), "social_proof", 3.0),
    (re.compile(r"\b(peer|benchmark|compare)\b", re.I), "social_proof", 1.5),
    (re.compile(r"\b(तुलना|ஒப்பீடு|তুলনা|పోల్చండి)\b", re.I), "social_proof", 2.0),

    # ── ET Research / macro (PS6) — keep "explain" weak so general_chat can win ──
    (re.compile(r"\b(deep.?dive|detailed.?guide|research.?report|macro.?view|rbi.?policy|repo.?rate|fii.?flow)\b", re.I), "et_research", 3.0),
    (re.compile(r"\b(how.?will.+affect.+my.?portfolio|portfolio.?impact|sector.?rotation|compare.?nifty)\b", re.I), "et_research", 2.8),
    (re.compile(r"\b(research.?on|market.?research|economic.?outlook)\b", re.I), "et_research", 2.0),
    (re.compile(r"\b(explain|what.?is|how.?does|guide|knowledge)\b", re.I), "et_research", 0.35),
    (re.compile(r"\b(समझाओ|बताओ|जानकारी|விளக்கம்|ব্যাখ্যা|వివరించు)\b", re.I), "et_research", 0.35),

    # ── Human Handoff ──
    (re.compile(r"\b(talk.?to.+human|mis.?sell|sebi.?complaint|fraud)\b", re.I), "human_handoff", 3.0),
    (re.compile(r"\b(advisor|expert|stressed|panicking|confused|complex)\b", re.I), "human_handoff", 2.0),
    (re.compile(r"\b(सलाहकार|विशेषज्ञ|मदद|ஆலோசகர்|উপদেষ্টা|సలహాదారు)\b", re.I), "human_handoff", 2.0),

    # ── Family Wealth ──
    (re.compile(r"\b(family.?wealth|family.?net.?worth|household.?finance|family.?portfolio|combined.?wealth)\b", re.I), "family_wealth", 3.0),
    (re.compile(r"\b(family|household|sibling)\b", re.I), "family_wealth", 1.0),
    (re.compile(r"\b(परिवार|माता-पिता|குடும்பம்|পরিবার|కుటుంబం|ಕುटుंబ|કુટુંબ)\b", re.I), "family_wealth", 1.5),

    # ── RAG — regulations, government schemes ──
    (re.compile(r"\b(ppf|nps|epf|atal.?pension|sukanya|pmjjby|pmsby|sgb|scss)\b", re.I), "rag_query", 3.0),
    (re.compile(r"\b(rbi|sebi|government.?scheme|regulation)\b", re.I), "rag_query", 2.0),
    (re.compile(r"\b(सरकारी.?योजना|सुकन्या|அரசு.?திட்டம்|সরকারি.?প্রকল্প|ప్రభుత్వ.?పథకం)\b", re.I), "rag_query", 2.0),
]


def keyword_score_classify(message: str) -> list[tuple[str, float]]:
    """
    Weighted keyword scoring — Tier 2 of the 4-tier cascade.

    Returns a sorted list of (intent, total_score) in descending order.
    Empty list if nothing matched.
    """
    msg = message.strip()
    if len(msg) < 2:
        return []

    scores: dict[str, float] = defaultdict(float)
    for pattern, intent, weight in _WEIGHTED_RULES:
        if pattern.search(msg):
            scores[intent] += weight

    if not scores:
        return []
    return sorted(scores.items(), key=lambda x: -x[1])


# ── Backward-compatible wrapper (used in existing code) ────────────────

def keyword_pre_classify(message: str) -> str | None:
    """
    Legacy wrapper — returns single intent or None.
    Prefer keyword_score_classify() for the new 4-tier engine.
    """
    matches = keyword_score_classify(message)
    if not matches:
        return None
    top_intent, top_score = matches[0]
    second_score = matches[1][1] if len(matches) > 1 else 0.0
    if top_score >= 3.0 or (top_score >= 1.5 and top_score - second_score >= 1.0):
        return top_intent
    return None
