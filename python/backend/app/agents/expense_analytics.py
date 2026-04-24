"""
Expense Analytics agent — detailed spending breakdown, category analysis, trends.
Uses profile data + LLM to generate smart spending insights.
"""
import logging
from typing import Any

from app.core.llm import primary_llm
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
    """Generate expense analytics from profile data."""
    profile = state.get("user_profile") or {}

    income = profile.get("monthly_income", 50000)
    expenses = profile.get("monthly_expenses", 30000)
    emi = profile.get("monthly_emi", 0)
    city = profile.get("city", "Mumbai")
    age = profile.get("age", 30)
    employment = profile.get("employment_type", "salaried")
    dependents = profile.get("dependents", 0)
    surplus = income - expenses

    try:
        import json
        result = await primary_llm.ainvoke(_EXPENSE_PROMPT.format(
            income=income, expenses=expenses, city=city, age=age,
            employment=employment, dependents=dependents, emi=emi,
            surplus=surplus,
            annual_spending=int(expenses * 12),
            annual_saving=int(surplus * 12),
        ))
        text = result.content.strip()
        # Extract JSON from response (strip markdown if present)
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        analysis = json.loads(text)
    except Exception as e:
        logger.error("Expense analytics LLM failed: %s", e)
        # Fallback with reasonable defaults
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


async def run_expense_analytics(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "expense analytics", "intent": "expense_analytics",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "expense_analytics", "expense analytics", language, voice_mode)
    return {"analysis": output, "response": response}
