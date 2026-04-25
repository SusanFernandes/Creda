"""
Onboarding agent — conversational profile building for new users.
Asks questions progressively, stores answers to UserProfile.
"""
from typing import Any

from app.core.llm import fast_llm, invoke_llm
from app.agents.state import FinancialState

_ONBOARDING_PROMPT = """You are CREDA, a friendly financial coach starting an onboarding conversation.
The user has completed these profile fields: {completed}
The user still needs to provide: {missing}

Based on the conversation so far and the user's latest message, do ONE of:
1. If the user provided information, acknowledge it and extract the data.
2. Ask for the NEXT missing field in a friendly, conversational way.
3. If all fields are complete, congratulate them and summarize their profile.

Latest message: {message}
Conversation history: {history}

Respond conversationally. Ask only ONE question at a time. Use ₹ for currency."""

_REQUIRED_FIELDS = [
    "name", "age", "city", "monthly_income", "monthly_expenses",
    "risk_appetite", "employment_type", "dependents",
    "has_health_insurance", "emergency_fund",
]


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    completed = [f for f in _REQUIRED_FIELDS if profile.get(f) not in (None, 0, "", False)]
    missing = [f for f in _REQUIRED_FIELDS if f not in completed]

    # Extract any data from the user's message
    extracted = _extract_profile_data(state.get("message", ""))

    if not missing and not extracted:
        return {
            "status": "complete",
            "message": "Onboarding complete! All required profile fields are filled.",
            "profile_summary": {f: profile.get(f) for f in _REQUIRED_FIELDS},
        }

    try:
        result = await invoke_llm(fast_llm, _ONBOARDING_PROMPT.format(
            completed=completed,
            missing=missing,
            message=state.get("message", ""),
            history=state.get("history", [])[-5:],
        ))
        response = result.content.strip()
    except Exception:
        next_field = missing[0] if missing else "name"
        response = f"Could you tell me your {next_field.replace('_', ' ')}?"

    return {
        "status": "in_progress",
        "completed_fields": completed,
        "missing_fields": missing,
        "extracted_data": extracted,
        "message": response,
    }


def _extract_profile_data(message: str) -> dict:
    """Basic extraction of profile data from free-text message."""
    import re
    extracted = {}

    # Age — handles 1-3 digit ages (e.g. "I'm 23", "age 5", "102 years old")
    age_match = re.search(r"\b(\d{1,3})\s*(?:years?\s*old|yrs?|age)\b", message, re.I)
    if not age_match:
        age_match = re.search(r"\bage\s*(?:is)?\s*(\d{1,3})\b", message, re.I)
    if not age_match:
        # standalone "I'm 25" / "i am 30" pattern
        age_match = re.search(r"\bi(?:'m|\s+am)\s+(\d{1,3})\b", message, re.I)
    if age_match:
        age_val = int(age_match.group(1))
        if 1 <= age_val <= 120:
            extracted["age"] = age_val

    # Income (₹ or rs or inr followed by number, or number followed by currency/pm)
    income_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(?:per month|monthly|/month|pm|p\.m)?", message, re.I)
    if not income_match:
        income_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:₹|rs|inr)?\s*(?:per month|monthly|/month|pm|p\.m)", message, re.I)
    if not income_match:
        # "income is 50000" or "salary 80000"
        income_match = re.search(r"(?:income|salary|earn|earning)\s*(?:is)?\s*(?:₹|rs\.?)?\s*([\d,]+)", message, re.I)
    if income_match:
        val_str = income_match.group(1).replace(",", "")
        val = float(val_str)
        # Handle lakh/crore
        if re.search(r"lakh|lac", message, re.I):
            val *= 100000
        elif re.search(r"crore|cr", message, re.I):
            val *= 10000000
        if val > 1000:
            extracted["monthly_income"] = val

    # City — extended list of Indian cities
    cities = [
        "mumbai", "delhi", "new delhi", "bangalore", "bengaluru", "hyderabad", "chennai",
        "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "chandigarh", "kochi",
        "indore", "noida", "gurgaon", "gurugram", "surat", "nagpur", "bhopal",
        "visakhapatnam", "vizag", "patna", "vadodara", "coimbatore", "thiruvananthapuram",
        "trivandrum", "thrissur", "dehradun", "ranchi", "guwahati", "bhubaneswar",
        "mysore", "mysuru", "mangalore", "mangaluru", "madurai", "varanasi",
        "agra", "nashik", "faridabad", "meerut", "rajkot", "kalyan", "thane",
        "navi mumbai", "goa", "panaji", "pondicherry", "puducherry", "shimla",
        "jodhpur", "udaipur", "amritsar", "ludhiana", "kanpur", "allahabad",
        "prayagraj", "raipur", "vijayawada", "aurangabad", "jabalpur", "gwalior",
        "hubli", "tiruchirappalli", "trichy", "salem", "warangal", "guntur",
    ]
    msg_lower = message.lower()
    for city in cities:
        if city in msg_lower:
            # Normalize common aliases
            normalized = {
                "bengaluru": "Bangalore", "gurugram": "Gurgaon",
                "trivandrum": "Thiruvananthapuram", "vizag": "Visakhapatnam",
                "mysuru": "Mysore", "mangaluru": "Mangalore",
                "prayagraj": "Allahabad", "puducherry": "Pondicherry",
                "trichy": "Tiruchirappalli", "new delhi": "Delhi",
                "navi mumbai": "Navi Mumbai",
            }
            extracted["city"] = normalized.get(city, city.title())
            break

    # Risk appetite
    if any(w in message.lower() for w in ["aggressive", "high risk", "adventurous"]):
        extracted["risk_appetite"] = "aggressive"
    elif any(w in message.lower() for w in ["conservative", "low risk", "safe", "cautious"]):
        extracted["risk_appetite"] = "conservative"
    elif any(w in message.lower() for w in ["moderate", "balanced", "medium"]):
        extracted["risk_appetite"] = "moderate"

    # Name extraction ("my name is X" / "I'm X" / "call me X")
    name_match = re.search(r"(?:my name is|i'?m|call me|name:\s*)([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", message)
    if name_match:
        extracted["name"] = name_match.group(1).strip()

    # Dependents
    dep_match = re.search(r"(\d+)\s*(?:dependents?|kids?|children|family members?)", message, re.I)
    if dep_match:
        extracted["dependents"] = int(dep_match.group(1))

    return extracted
