"""Profile completeness checks — no silent defaults for critical inputs."""

from __future__ import annotations

from typing import Any

REQUIRED_FIELDS = {
    "tier_1": ["monthly_income", "monthly_expenses", "age"],
    "tier_2": ["employment_type", "city", "risk_tolerance"],
    "tier_3": ["fire_target_age", "epf_balance", "cams_uploaded"],
    "tax": [
        "rent_paid",
        "basic_salary",
        "has_nps",
        "self_health_premium",
        "parents_health_premium",
        "parents_age_above_60",
        "section_80c_amount",
    ],
}


def _normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Map legacy column names and aliases so REQUIRED_FIELDS resolve correctly."""
    p = dict(profile)
    if not p.get("risk_tolerance") and p.get("risk_appetite"):
        p["risk_tolerance"] = p["risk_appetite"]
    if p.get("section_80c_amount") in (None, 0) and p.get("investments_80c"):
        p["section_80c_amount"] = p["investments_80c"]
    if p.get("self_health_premium") in (None, 0) and p.get("health_insurance_premium"):
        p["self_health_premium"] = p["health_insurance_premium"]
    return p


def _value_missing(field: str, val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, bool):
        if field == "cams_uploaded":
            return val is not True
        if field in ("has_nps", "parents_age_above_60"):
            return False
        return False
    if val == 0 or val == "":
        return True
    return False


def check_profile(profile: dict[str, Any], required_tiers: list[str]) -> dict[str, Any]:
    p = _normalize_profile(profile)
    missing: list[str] = []
    for tier in required_tiers:
        for field in REQUIRED_FIELDS[tier]:
            val = p.get(field)
            if _value_missing(field, val):
                missing.append(field)
    total_fields = sum(
        len(REQUIRED_FIELDS[k]) for k in required_tiers if k in REQUIRED_FIELDS
    )
    if total_fields == 0:
        completeness_pct = 100.0
    else:
        completeness_pct = round(100 * (1 - len(missing) / total_fields), 1)
    return {
        "missing": missing,
        "completeness_pct": completeness_pct,
        "is_complete": len(missing) == 0,
    }


SKIP_PROFILE_GUARD = frozenset({
    "general_chat",
    "rag_query",
    "onboarding",
    "human_handoff",
    "et_research",
    "market_pulse",
})


def guard_for_intent(intent: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    """
    Intent-specific completeness. FIRE needs fire_target_age after tier_1.
    Tax wizard requires tax tier fields.
    """
    if intent in SKIP_PROFILE_GUARD:
        return {"missing": [], "completeness_pct": 100.0, "is_complete": True}
    p = _normalize_profile(profile or {})
    if intent in ("fire_planner", "stress_test"):
        g1 = check_profile(p, ["tier_1"])
        if not g1["is_complete"]:
            return g1
        fta = p.get("fire_target_age")
        if fta is None or fta == 0:
            return {
                "missing": ["fire_target_age"],
                "completeness_pct": round(g1["completeness_pct"] * 0.95, 1),
                "is_complete": False,
            }
        return {"missing": [], "completeness_pct": 100.0, "is_complete": True}
    if intent in ("tax_wizard", "tax_copilot"):
        return check_profile(p, ["tier_1", "tax"])
    return check_profile(p, ["tier_1"])
