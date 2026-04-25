"""
Expense Analytics agent — detailed spending breakdown, category analysis, trends.
Uses profile data + LLM to generate smart spending insights.
"""
import logging
from typing import Any

from app.core.llm import fast_llm, invoke_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.expense_analytics")

_EXPENSE_PROMPT = """You are CREDA's Expense Analytics Engine for Indian users.

User profile:
- Monthly income: ₹{income:,.0f}
- Monthly expenses: ₹{expenses:,.0f}
- City: {city}
- Age: {age}
- Employment: {employment}
- Dependents: {dependents}
- EMI: ₹{emi:,.0f}

Generate a realistic, detailed monthly expense BREAKDOWN. Use typical Indian spending patterns for a {city}-based {employment} person with ₹{income:,.0f} income.

Return ONLY a valid JSON object (no markdown, no explanation) with this structure:
{{
  "categories": [
    {{"name": "Rent/Housing", "amount": 15000, "pct": 23, "trend": "stable", "insight": "Consider if you're in the right locality for value"}},
    {{"name": "Groceries", "amount": 8000, "pct": 12, "trend": "up", "insight": "Try weekly batch cooking to save 15%"}}
  ],
  "top_savings_opportunities": [
    {{"category": "Dining Out", "current": 5000, "target": 3000, "monthly_saving": 2000, "tip": "Cook at home 3x more per week"}}
  ],
  "spending_score": 72,
  "spending_personality": "Balanced Spender",
  "monthly_surplus": {surplus},
  "annual_projection": {{
    "total_spending": {annual_spending},
    "total_saving": {annual_saving},
    "if_saved_more": "Saving ₹5000 more/month = ₹60K/year extra → ₹8.5L in 10 years at 12% returns"
  }}
}}"""


async def run(state: FinancialState) -> dict[str, Any]:
    """Generate expense analytics from profile data or real expenses."""
    profile = state.get("user_profile") or {}
    real_expenses = state.get("real_expenses")
    budget_data = state.get("budget_data")

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    emi = profile.get("monthly_emi", 0)
    city = profile.get("city", "Mumbai")
    age = profile.get("age", 30)
    employment = profile.get("employment_type", "salaried")
    dependents = profile.get("dependents", 0)
    surplus = income - expenses

    # If real expense data exists, build analysis from it (no LLM needed for categories)
    if real_expenses:
        total_spent = sum(real_expenses.values())
        categories = []
        for cat, amount in sorted(real_expenses.items(), key=lambda x: -x[1]):
            pct = round(amount / total_spent * 100) if total_spent > 0 else 0
            # Check budget for this category
            budget_info = budget_data.get(cat, {}) if budget_data else {}
            planned = budget_info.get("planned", amount)
            trend = "up" if amount > planned * 1.1 else ("down" if amount < planned * 0.9 else "stable")
            insight = ""
            if amount > planned * 1.2 and planned > 0:
                insight = f"Over budget by ₹{int(amount - planned):,}. Consider setting spending limits."
            elif amount < planned * 0.8 and planned > 0:
                insight = f"Under budget by ₹{int(planned - amount):,}. Great discipline!"
            categories.append({
                "name": cat, "amount": int(amount), "pct": pct,
                "trend": trend, "insight": insight,
                "planned": int(planned),
            })

        # Calculate savings opportunities from over-budget categories
        top_savings = []
        for cat_info in categories:
            if cat_info.get("planned") and cat_info["amount"] > cat_info["planned"]:
                saving = cat_info["amount"] - cat_info["planned"]
                top_savings.append({
                    "category": cat_info["name"],
                    "current": cat_info["amount"],
                    "target": cat_info["planned"],
                    "monthly_saving": saving,
                    "tip": f"Reduce {cat_info['name']} spending by ₹{saving:,}/month to stay on budget.",
                })

        # Spending score (penalize over-budget categories)
        if budget_data:
            budget_adherence = sum(1 for c in categories if c["trend"] != "up") / max(len(categories), 1)
            spending_score = int(50 + budget_adherence * 50)
        else:
            savings_rate = surplus / income if income > 0 else 0
            spending_score = min(100, int(savings_rate * 200))

        analysis = {
            "categories": categories,
            "top_savings_opportunities": top_savings[:3],
            "spending_score": spending_score,
            "spending_personality": "Budget-Conscious" if spending_score >= 70 else ("Balanced Spender" if spending_score >= 50 else "Liberal Spender"),
            "monthly_surplus": int(income - total_spent),
            "annual_projection": {
                "total_spending": int(total_spent * 12),
                "total_saving": int((income - total_spent) * 12),
                "if_saved_more": f"Saving ₹5,000 more/month = ₹60K/year extra → ₹8.5L in 10 years at 12% returns",
            },
        }
    else:
        # Fallback: LLM-generated analysis from profile data
        try:
            import json
            result = await invoke_llm(fast_llm, _EXPENSE_PROMPT.format(
                income=income, expenses=expenses, city=city, age=age,
                employment=employment, dependents=dependents, emi=emi,
                surplus=surplus,
                annual_spending=int(expenses * 12),
                annual_saving=int(surplus * 12),
            ))
            text = result.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            analysis = json.loads(text)
        except Exception as e:
            logger.error("Expense analytics LLM failed: %s", e)
            analysis = {
                "categories": [
                    {"name": "Rent/Housing", "amount": int(expenses * 0.30), "pct": 30, "trend": "stable", "insight": ""},
                    {"name": "Groceries", "amount": int(expenses * 0.15), "pct": 15, "trend": "stable", "insight": ""},
                    {"name": "Transport", "amount": int(expenses * 0.10), "pct": 10, "trend": "stable", "insight": ""},
                    {"name": "Utilities", "amount": int(expenses * 0.08), "pct": 8, "trend": "stable", "insight": ""},
                    {"name": "Dining Out", "amount": int(expenses * 0.10), "pct": 10, "trend": "up", "insight": ""},
                    {"name": "Shopping", "amount": int(expenses * 0.10), "pct": 10, "trend": "stable", "insight": ""},
                    {"name": "EMI", "amount": int(emi), "pct": int(emi / expenses * 100) if expenses else 0, "trend": "stable", "insight": ""},
                    {"name": "Other", "amount": int(expenses * 0.07), "pct": 7, "trend": "stable", "insight": ""},
                ],
                "top_savings_opportunities": [],
                "spending_score": 65,
                "spending_personality": "Average Spender",
                "monthly_surplus": surplus,
                "annual_projection": {
                    "total_spending": int(expenses * 12),
                    "total_saving": int(surplus * 12),
                },
            }

    # Add summary stats
    analysis["monthly_income"] = income
    analysis["monthly_expenses"] = expenses
    analysis["savings_rate"] = round(surplus / income * 100, 1) if income > 0 else 0

    return analysis


async def run_expense_analytics(profile, language: str, voice_mode: bool, expenses=None, budgets=None) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}

    # If real expenses exist, aggregate them by category
    real_expense_data = None
    budget_data = None
    if expenses:
        from collections import defaultdict
        cat_totals = defaultdict(float)
        for exp in expenses:
            cat_totals[exp.category] += exp.amount
        real_expense_data = dict(cat_totals)
    if budgets:
        budget_data = {b.category: {"planned": b.planned_amount, "actual": b.actual_amount} for b in budgets}

    state: FinancialState = {
        "user_id": profile.user_id, "message": "expense analytics", "intent": "expense_analytics",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
        "real_expenses": real_expense_data,
        "budget_data": budget_data,
    }
    output = await run(state)
    response = await synthesize(output, "expense_analytics", "expense analytics", language, voice_mode)
    return {"analysis": output, "response": response}
