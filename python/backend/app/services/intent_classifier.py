"""
Keyword pre-classifier — router-level gate, runs BEFORE LangGraph.

Saves a Groq API call for ~90% of queries by matching known keyword patterns.
Returns None when uncertain → caller falls through to LLM intent classifier.
Supports English + Hindi + Tamil + Telugu + Bengali + Marathi + Kannada + Gujarati keywords.
"""
import re

# ── Keyword → intent mapping (multilingual) ───────────────────────────
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Portfolio X-Ray
    (re.compile(
        r"\b(cams|kfintech|mutual fund|portfolio|xirr|xray|x-ray|holdings|nav|sip return|fund overlap|expense ratio"
        r"|म्यूचुअल फंड|पोर्टफोलियो|म्युचुअल|निवेश|ம்யூசுவல் ஃபண்ட்|போர்ட்ஃபோலியோ|পোর্টফোলিও|মিউচুয়াল ফান্ড"
        r"|पोर्टफोलिओ|ಮ್ಯೂಚುಯಲ್ ಫಂಡ್|పోర్ట్‌ఫోలియో|మ్యూచువల్ ఫండ్"
        r")\b", re.I), "portfolio_xray"),
    # Stress Test
    (re.compile(
        r"\b(stress test|what if|market crash|job loss|baby|marriage impact|life event|scenario|monte carlo"
        r"|तनाव परीक्षण|नौकरी छूट|बाजार गिरावट|शादी|बच्चा|что если"
        r")\b", re.I), "stress_test"),
    # FIRE Planner
    (re.compile(
        r"\b(fire|early retire|retirement|retire early|financial independence|fire number|corpus target|4% rule"
        r"|रिटायरमेंट|सेवानिवृत्ति|जल्दी रिटायर|ஓய்வு|రిటైర్మెంట్|অবসর|निवृत्ती"
        r")\b", re.I), "fire_planner"),
    # Tax Wizard
    (re.compile(
        r"\b(tax|80c|80d|80ccd|hra|home loan interest|old regime|new regime|deduction|itr|form 16|tax saving|elss"
        r"|टैक्स|कर बचत|कर कटौती|आयकर|வரி|పన్ను|ন্যায়|कर|ट\u0945क्स"
        r")\b", re.I), "tax_wizard"),
    # Money Health Score
    (re.compile(
        r"\b(health score|money health|financial health|financial score|credit score|emergency fund check|insurance check"
        r"|वित्तीय स्वास्थ्य|आपातकालीन फंड|பணம் ஆரோக்கியம்|আর্থিক স্বাস্থ্য"
        r")\b", re.I), "money_health"),
    # Budget Coach
    (re.compile(
        r"\b(budget|spending|expense track|overspend|50.30.20|savings rate|cut cost|monthly budget"
        r"|बजट|खर्च|बचत|ব\u09be\u099c\u09c7\u099f|खर्चा|వ\u0c46\u0c1a\u0c4d\u0c1a\u0c02"
        r")\b", re.I), "budget_coach"),
    # Goal Planner
    (re.compile(
        r"\b(goal|target amount|save for|house|car|education|wedding|down payment|goal plan"
        r"|लक्ष्य|बच्चों की शिक्षा|घर|गाड़ी|शादी|இலக்கு|கல்வி|লক্ষ্য|ध्येय|ಗುರಿ|లక్ష\u0c4dయం"
        r")\b", re.I), "goal_planner"),
    # Couples Finance
    (re.compile(
        r"\b(couple|partner|spouse|joint|split|shared expense|combined income|marriage finance"
        r"|पति|पत्नी|जोड़ा|साझा खर्च|கணவன்|மனைவி|দম্পতি|జంట|दांपत्य"
        r")\b", re.I), "couples_finance"),
    # SIP Calculator
    (re.compile(
        r"\b(sip calculator|sip amount|monthly sip|step.up sip|sip return|how much sip"
        r"|एसआईपी|सिप|எஸ்ஐபி|ఎస్\u200cఐపీ|এসআইপি"
        r")\b", re.I), "sip_calculator"),
    # Market Pulse
    (re.compile(
        r"\b(market|nifty|sensex|stock|bull|bear|correction|rally|fii|dii|market today|market news|index"
        r"|बाजार|शेयर|निफ्टी|सेंसेक्स|சந்தை|நிஃப்டி|বাজার|बाजार|మార్కెట్|ಮಾರುಕಟ್ಟೆ"
        r")\b", re.I), "market_pulse"),
    # Tax Copilot
    (re.compile(
        r"\b(tax.?loss|harvest|tax copilot|advance tax|tax deadline|tax optimization|year.?round tax|tax planning"
        r"|अग्रिम कर|कर नियोजन|வரி திட்டமிடல்|অগ্রিম কর"
        r")\b", re.I), "tax_copilot"),
    # Money Personality
    (re.compile(
        r"\b(personality|money type|financial personality|risk profile|investor type|behavioural|behavioral|money mindset"
        r"|व्यक्तित्व|निवेशक प्रकार|ஆளுமை|ব্যক্তিত্ব|వ్యక్తిత్వం"
        r")\b", re.I), "money_personality"),
    # Goal Simulator
    (re.compile(
        r"\b(simulat|what if.*sip|what if.*return|scenario model|goal simulator|drag.*slider|adjust.*sip"
        r"|सिमुलेशन|அனுகரிப্পு|সিমুলেশন"
        r")\b", re.I), "goal_simulator"),
    # Social Proof
    (re.compile(
        r"\b(peer|people like me|others|crowd|benchmark|compare|how do i stack|age group|similar investor"
        r"|तुलना|comparar|ஒப்பீடு|তুলনা|పోల్చండి"
        r")\b", re.I), "social_proof"),
    # ET Research
    (re.compile(
        r"\b(research|article|explain|what is|how does|guide|learn|knowledge|deep dive|detailed"
        r"|समझाओ|बताओ|जानकारी|விளக்கம்|ব্যাখ্যা|వివరించు"
        r")\b", re.I), "et_research"),
    # Human Handoff
    (re.compile(
        r"\b(talk to.*human|advisor|expert|help me|complex|confused|stressed|panicking|sebi|fraud|mis.?sell"
        r"|सलाहकार|विशेषज्ञ|मदद|ஆலோசகர்|উপদেষ্টা|సలహాదారు"
        r")\b", re.I), "human_handoff"),
    # Family Wealth
    (re.compile(
        r"\b(family|household|spouse|parent|child|sibling|combined.*wealth|family.*net worth|household.*finance|family.*portfolio"
        r"|परिवार|घर|माता-पिता|குடும்பம்|পরিবার|కుటుంబం|ಕುಟುಂಬ|કુટુંબ"
        r")\b", re.I), "family_wealth"),
    # RAG — regulations, general knowledge
    (re.compile(
        r"\b(rbi|sebi|ppf|nps|epf|atal pension|sukanya|pmjjby|pmsby|sgb|scss|government scheme|regulation"
        r"|सरकारी योजना|सुकन्या|அரசு திட்டம்|সরকারি প্রকল্প|ప్రభుత్వ పథకం"
        r")\b", re.I), "rag_query"),
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
