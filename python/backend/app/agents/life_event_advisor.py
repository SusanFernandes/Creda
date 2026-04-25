"""
Life Event Financial Advisor agent — the decision engine.
Handles: bonus, inheritance, marriage, new_baby, job_change, property_purchase.
Maps each event to a personalised, tax-bracket-aware action plan.
"""
import math
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

_LIFE_EVENT_PROMPT = """You are an elite Indian financial advisor handling a life event.
The user just reported: {event_description}

Their financial snapshot:
{snapshot}

Your structured deployment plan:
{plan}

Now write a warm, confident, Arjun-specific response. Use ₹ amounts, percentages, and deadlines.
Format it as a numbered priority list with allocation percentages.
End with the projected health score improvement.
Keep it under 250 words. Be specific, not generic."""

# Event-type decision trees
_EVENT_STRATEGIES = {
    "bonus": {
        "priorities": ["emergency_fund", "tax_optimization", "goal_acceleration", "investment"],
        "description": "Performance bonus / lump-sum income",
    },
    "inheritance": {
        "priorities": ["emergency_fund", "debt_payoff", "tax_optimization", "investment"],
        "description": "Inheritance / windfall",
    },
    "marriage": {
        "priorities": ["wedding_fund", "insurance", "joint_planning", "emergency_fund"],
        "description": "Upcoming marriage",
    },
    "new_baby": {
        "priorities": ["insurance", "emergency_fund", "education_fund", "will_creation"],
        "description": "New child",
    },
    "job_change": {
        "priorities": ["epf_transfer", "salary_restructure", "tax_replan", "investment_boost"],
        "description": "Job change / promotion",
    },
    "property_purchase": {
        "priorities": ["down_payment", "emi_planning", "insurance", "tax_benefits"],
        "description": "Property purchase",
    },
    "job_loss": {
        "priorities": ["emergency_runway", "emi_discipline", "insurance_continuity", "liquidity"],
        "description": "Job loss / unemployment",
    },
    "parent_support": {
        "priorities": ["cashflow", "emergency_buffer", "tax_planning"],
        "description": "Parent dependency / elder support",
    },
}


def _detect_event_type(message: str) -> tuple[str, float]:
    """Detect event type and amount from natural language."""
    import re
    msg = message.lower()

    # Detect amount
    amount = 0
    amount_patterns = [
        r'₹\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|l)',
        r'₹\s*([\d,]+(?:\.\d+)?)\s*(?:crore|cr)',
        r'₹\s*([\d,]+(?:\.\d+)?)',
        r'([\d,]+(?:\.\d+)?)\s*(?:lakh|lac|l)',
        r'([\d,]+(?:\.\d+)?)\s*(?:crore|cr)',
        r'rs\.?\s*([\d,]+(?:\.\d+)?)',
    ]
    for pat in amount_patterns:
        m = re.search(pat, msg)
        if m:
            val = float(m.group(1).replace(",", ""))
            if "crore" in msg or "cr" in msg:
                val *= 10000000
            elif "lakh" in msg or "lac" in msg or msg[m.end():m.end()+2].strip().startswith("l"):
                val *= 100000
            amount = val
            break

    # Detect event type
    if any(w in msg for w in ["bonus", "incentive", "variable pay", "performance"]):
        return "bonus", amount
    if any(w in msg for w in ["inherit", "windfall", "gift", "received money"]):
        return "inheritance", amount
    if any(w in msg for w in ["marr", "wedding", "engaged", "fiancé", "fiancee"]):
        return "marriage", amount
    if any(w in msg for w in ["baby", "child", "pregnant", "expecting", "newborn"]):
        return "new_baby", amount
    if any(w in msg for w in ["job change", "new job", "promotion", "hike", "appraisal", "switch"]):
        return "job_change", amount
    if any(w in msg for w in ["property", "house", "flat", "apartment", "real estate", "home buy"]):
        return "property_purchase", amount
    if any(
        w in msg
        for w in [
            "lost my job",
            "lost job",
            "got fired",
            "laid off",
            "layoff",
            "unemployed",
            "lost employment",
        ]
    ):
        return "job_loss", amount
    if any(w in msg for w in ["parent depend", "parents moving", "elder care", "support parents"]):
        return "parent_support", amount

    return "bonus", amount  # default to bonus if unclear


def _build_deployment_plan(
    event_type: str,
    amount: float,
    profile: dict,
    portfolio: dict,
    goals: list,
) -> dict:
    """Build a structured deployment plan based on event type and user context."""
    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    if expenses <= 0:
        expenses = 1.0
    emergency = profile.get("emergency_fund", 0)
    target_emergency = expenses * 6
    emergency_gap = max(target_emergency - emergency, 0)

    investments_80c = profile.get("investments_80c", 0)
    nps_contribution = profile.get("nps_contribution", 0)
    has_health = profile.get("has_health_insurance", False)
    life_cover = profile.get("life_insurance_cover", 0)
    age = profile.get("age", 30)

    portfolio_value = portfolio.get("current_value", 0) if portfolio else 0

    # Tax bracket estimation
    annual_income = income * 12
    if annual_income > 1500000:
        tax_rate = 0.30
    elif annual_income > 1200000:
        tax_rate = 0.20
    elif annual_income > 900000:
        tax_rate = 0.15
    elif annual_income > 600000:
        tax_rate = 0.10
    else:
        tax_rate = 0.05

    allocations = []
    remaining = amount

    if event_type == "bonus" or event_type == "inheritance":
        # Priority 1: Emergency fund
        if emergency_gap > 0:
            ef_alloc = min(emergency_gap, remaining * 0.40)
            allocations.append({
                "category": "Emergency Fund",
                "amount": round(ef_alloc),
                "pct": round(ef_alloc / amount * 100) if amount > 0 else 0,
                "reason": f"Currently ₹{emergency:,.0f} of ₹{target_emergency:,.0f} target ({expenses * 6:,.0f} = 6 months). "
                          f"Adding ₹{ef_alloc:,.0f} reaches ₹{emergency + ef_alloc:,.0f} — "
                          f"covering {(emergency + ef_alloc) / expenses:.1f} months.",
                "action": "Deposit in liquid fund or high-yield savings account",
            })
            remaining -= ef_alloc

        # Priority 2: Tax optimization
        tax_80c_gap = max(150000 - investments_80c, 0)
        tax_nps_gap = max(50000 - nps_contribution, 0)
        tax_total_gap = tax_80c_gap + tax_nps_gap

        if tax_total_gap > 0 and remaining > 0:
            tax_alloc = min(tax_total_gap, remaining * 0.25)
            tax_saved = round(tax_alloc * tax_rate)
            details = []
            if tax_80c_gap > 0:
                elss_amount = min(tax_80c_gap, tax_alloc)
                details.append(f"ELSS: ₹{elss_amount:,.0f}")
            if tax_nps_gap > 0 and tax_alloc > tax_80c_gap:
                nps_amount = min(tax_nps_gap, tax_alloc - tax_80c_gap)
                details.append(f"NPS 80CCD(1B): ₹{nps_amount:,.0f}")
            allocations.append({
                "category": "Tax Optimization",
                "amount": round(tax_alloc),
                "pct": round(tax_alloc / amount * 100) if amount > 0 else 0,
                "reason": f"Invest in {' + '.join(details)}. Saves ₹{tax_saved:,.0f} in taxes immediately. "
                          f"Effective first-year return: {tax_rate*100:.0f}%+.",
                "action": f"Invest before March 31 deadline",
            })
            remaining -= tax_alloc

        # Priority 3: Goal acceleration (pick the most urgent goal)
        if goals and remaining > 0:
            urgent_goal = None
            for g in goals:
                if isinstance(g, dict):
                    if g.get("goal_name", "").lower() not in ["fire corpus", "retirement"]:
                        if not urgent_goal or (g.get("target_date") and (not urgent_goal.get("target_date") or g["target_date"] < urgent_goal["target_date"])):
                            urgent_goal = g

            if urgent_goal:
                goal_gap = urgent_goal.get("target_amount", 0) - urgent_goal.get("current_saved", 0)
                goal_alloc = min(goal_gap * 0.15, remaining * 0.30)
                allocations.append({
                    "category": f"{urgent_goal['goal_name']} Fund",
                    "amount": round(goal_alloc),
                    "pct": round(goal_alloc / amount * 100) if amount > 0 else 0,
                    "reason": f"Need ₹{goal_gap:,.0f} more for {urgent_goal['goal_name']}. "
                              f"Park in liquid fund earning ~7% — don't lock it up.",
                    "action": "Park in liquid/ultra-short fund for easy access",
                })
                remaining -= goal_alloc

        # Priority 4: Long-term investment
        if remaining > 0:
            allocations.append({
                "category": "Long-Term Investment",
                "amount": round(remaining),
                "pct": round(remaining / amount * 100) if amount > 0 else 0,
                "reason": f"Start a dedicated SIP of ₹{round(remaining/3):,.0f}/month or lump-sum into flexi-cap/index fund.",
                "action": "Nifty 50 index fund or flexi-cap SIP",
            })

    elif event_type == "marriage":
        # Wedding-specific allocations
        if emergency_gap > 0:
            ef_alloc = min(emergency_gap, remaining * 0.25)
            allocations.append({
                "category": "Emergency Fund",
                "amount": round(ef_alloc),
                "pct": round(ef_alloc / amount * 100) if amount > 0 else 0,
                "reason": f"Build emergency buffer before wedding expenses hit.",
                "action": "High-yield savings or liquid fund",
            })
            remaining -= ef_alloc

        allocations.append({
            "category": "Wedding Fund",
            "amount": round(remaining * 0.40),
            "pct": round(remaining * 0.40 / amount * 100) if amount > 0 else 0,
            "reason": "Set aside for wedding expenses. Park in ultra-short debt fund.",
            "action": "Ultra-short duration debt fund",
        })
        remaining *= 0.60

        if life_cover < income * 12 * 10:
            allocations.append({
                "category": "Term Life Insurance",
                "amount": round(min(remaining * 0.10, 25000)),
                "pct": round(min(remaining * 0.10, 25000) / amount * 100) if amount > 0 else 0,
                "reason": f"Getting married — get ₹{income * 12 * 15:,.0f} term cover (15x annual income). Premium: ~₹{round(age * 500)}/year.",
                "action": "Buy term plan before wedding",
            })

        if remaining > 0:
            allocations.append({
                "category": "Joint Investment Start",
                "amount": round(remaining),
                "pct": round(remaining / amount * 100) if amount > 0 else 0,
                "reason": "Start joint SIP post-wedding for shared goals.",
                "action": "Flexi-cap SIP in one partner's name for now",
            })

    elif event_type == "new_baby":
        if life_cover < income * 12 * 15:
            allocations.append({
                "category": "Life Insurance Upgrade",
                "amount": round(min(remaining * 0.10, 30000)),
                "pct": 10,
                "reason": f"Increase term cover to ₹{income * 12 * 20:,.0f} (20x income with dependent child).",
                "action": "Increase existing term plan or buy additional cover",
            })
            remaining *= 0.90

        allocations.append({
            "category": "Emergency Fund Top-Up",
            "amount": round(remaining * 0.30),
            "pct": 30,
            "reason": "Expenses will increase — build 8-month buffer.",
            "action": "Liquid fund",
        })
        allocations.append({
            "category": "Child Education Fund",
            "amount": round(remaining * 0.40),
            "pct": 40,
            "reason": "Start early — ₹50L education goal in 18 years needs only ₹5,000/month SIP at 12%.",
            "action": "Flexi-cap or balanced advantage fund SIP",
        })
        allocations.append({
            "category": "Will & Nomination Update",
            "amount": 0,
            "pct": 0,
            "reason": "Update all MF nominations, insurance beneficiary, and create a will.",
            "action": "Use online will service or consult lawyer",
        })

    elif event_type == "job_loss":
        runway = expenses * 6
        months_cover = (float(emergency or 0) / expenses) if expenses > 0 else 0
        if amount > 0:
            park = round(amount * 0.65)
            allocations.append({
                "category": "Severance — park in liquid",
                "amount": park,
                "pct": 65,
                "reason": f"Keep most severance liquid while job hunting. Current runway ~{months_cover:.1f} months of expenses.",
                "action": "Liquid / money-market funds",
            })
        allocations.append({
            "category": "Emergency runway target",
            "amount": 0,
            "pct": 0,
            "reason": f"Aim for ₹{runway:,.0f} (6 months). You have ₹{float(emergency or 0):,.0f} — gap ₹{max(runway - float(emergency or 0), 0):,.0f}.",
            "action": "Pause discretionary SIPs if needed; keep health insurance active",
        })

    elif event_type == "parent_support":
        monthly_support = amount if amount > 0 else round(expenses * 0.12)
        annual = monthly_support * 12
        allocations.append({
            "category": "Parent support (annualised)",
            "amount": annual,
            "pct": 100,
            "reason": f"Budget ~₹{monthly_support:,.0f}/month for support; track separately from your FIRE SIPs.",
            "action": "Standing instruction + document 80D premiums if paying parents' health cover",
        })

    else:
        # Generic fallback
        allocations.append({
            "category": "Financial Planning",
            "amount": round(amount),
            "pct": 100,
            "reason": f"Consult with CREDA's AI for a detailed plan based on your specific situation.",
            "action": "Chat with CREDA for personalized advice",
        })

    # Estimate health score improvement
    current_score = _estimate_health_score(profile, portfolio)
    projected_profile = dict(profile)
    for alloc in allocations:
        if alloc["category"] == "Emergency Fund":
            projected_profile["emergency_fund"] = emergency + alloc["amount"]
        elif alloc["category"] == "Tax Optimization":
            projected_profile["investments_80c"] = min(investments_80c + alloc["amount"], 150000)
    projected_score = _estimate_health_score(projected_profile, portfolio)

    return {
        "event_type": event_type,
        "event_amount": amount,
        "allocations": allocations,
        "total_deployed": sum(a["amount"] for a in allocations),
        "current_health_score": current_score,
        "projected_health_score": projected_score,
        "score_improvement": projected_score - current_score,
    }


def _estimate_health_score(profile: dict, portfolio: dict) -> int:
    """Quick health score estimation matching money_health.py logic."""
    income = float(profile.get("monthly_income") or 0) or 1.0
    expenses = float(profile.get("monthly_expenses") or 0) or 1.0
    emergency = profile.get("emergency_fund", 0)
    life_cover = profile.get("life_insurance_cover", 0)
    has_health = profile.get("has_health_insurance", False)
    monthly_emi = profile.get("monthly_emi", 0)
    investments_80c = profile.get("investments_80c", 0)
    portfolio_value = portfolio.get("current_value", 0) if portfolio else 0
    age = profile.get("age", 30)

    # Emergency (20%)
    target_ef = expenses * 6
    ef_score = min(round(emergency / target_ef * 100), 100) if target_ef > 0 else 50

    # Insurance (20%)
    annual_income = income * 12
    rec_life = annual_income * 15
    life_s = min(round(life_cover / rec_life * 100), 100) if rec_life > 0 else 0
    health_s = 100 if has_health else 0
    ins_score = round(life_s * 0.6 + health_s * 0.4)

    # Diversification (15%)
    div_score = 50  # simplified

    # Debt (20%)
    emi_ratio = (monthly_emi / income * 100) if income > 0 else 0
    debt_score = 100 if emi_ratio == 0 else 90 if emi_ratio <= 25 else 70 if emi_ratio <= 35 else 40

    # Tax (10%)
    tax_score = min(round(investments_80c / 150000 * 100), 100) if investments_80c > 0 else 0

    # Retirement (15%)
    target_by_age = annual_income * max((age - 20) / 10, 0.5)
    total_savings = portfolio_value + profile.get("epf_balance", 0) + profile.get("ppf_balance", 0)
    ret_score = min(round(total_savings / target_by_age * 100), 100) if target_by_age > 0 else 50

    overall = (ef_score * 20 + ins_score * 20 + div_score * 15 + debt_score * 20 + tax_score * 10 + ret_score * 15) / 100
    return round(overall)


async def run(state: FinancialState) -> dict[str, Any]:
    """Run the life event advisor."""
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    goals = state.get("goals_data") or []
    message = state.get("message", "")

    event_type, amount = _detect_event_type(message)
    strategy = _EVENT_STRATEGIES.get(event_type, _EVENT_STRATEGIES["bonus"])

    plan = _build_deployment_plan(event_type, amount, profile, portfolio, goals)

    # LLM enrichment
    snapshot = {
        "name": profile.get("name", "User"),
        "age": profile.get("age", 30),
        "income": profile.get("monthly_income", 0),
        "expenses": profile.get("monthly_expenses", 0),
        "emergency_fund": profile.get("emergency_fund", 0),
        "portfolio_value": portfolio.get("current_value", 0) if portfolio else 0,
        "80c_done": profile.get("investments_80c", 0),
        "life_insurance": profile.get("life_insurance_cover", 0),
        "has_health_insurance": profile.get("has_health_insurance", False),
    }

    try:
        result = await primary_llm.ainvoke(_LIFE_EVENT_PROMPT.format(
            event_description=f"{strategy['description']} — ₹{amount:,.0f}" if amount else strategy['description'],
            snapshot=str(snapshot),
            plan=str(plan),
        ))
        plan["advice"] = result.content.strip()
    except Exception:
        plan["advice"] = ""

    return plan


async def run_life_event_advisor(
    profile, portfolio, goals_list, message: str, language: str, voice_mode: bool
) -> dict:
    """Wrapper called from the agents router."""
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    portfolio_dict = None
    if portfolio:
        portfolio_dict = {
            "total_invested": portfolio.total_invested,
            "current_value": portfolio.current_value,
            "xirr": portfolio.xirr,
        }
    goals_data = []
    for g in goals_list:
        goals_data.append({
            "goal_name": g.goal_name,
            "target_amount": g.target_amount,
            "target_date": g.target_date.isoformat() if g.target_date else None,
            "current_saved": g.current_saved,
            "is_on_track": g.is_on_track,
        })

    state: FinancialState = {
        "user_id": profile.user_id,
        "message": message,
        "intent": "life_event_advisor",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
        "portfolio_data": portfolio_dict,
        "goals_data": goals_data,
    }
    output = await run(state)
    response = await synthesize(output, "life_event_advisor", message, language, voice_mode)
    return {"analysis": output, "response": response}
