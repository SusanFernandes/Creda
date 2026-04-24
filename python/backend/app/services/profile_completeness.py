"""
Single place for "what is missing from the profile" so agents and Settings stay aligned.
Treat 0 / empty as missing for monetary fields that must come from the user (no invented defaults).
"""
from __future__ import annotations

from typing import Any

# Fields we prompt for in Settings / onboarding — keys match UserProfile columns.
_FIELD_LABELS: dict[str, str] = {
    "monthly_income": "Monthly income (₹)",
    "monthly_expenses": "Monthly expenses (₹)",
    "emergency_fund": "Emergency fund balance (₹)",
    "city": "City (for metro HRA / tax)",
    "rent_paid": "Monthly rent paid (₹) — for HRA exemption in old regime",
    "hra": "Monthly HRA from payslip (₹)",
    "age": "Age",
    "fire_target_age": "Target retirement / FIRE age (must be after your current age)",
}


def profile_as_dict(profile: Any) -> dict[str, Any]:
    if profile is None:
        return {}
    if isinstance(profile, dict):
        return profile
    return {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}


def _missing_money_income_expenses(p: dict[str, Any]) -> list[str]:
    out: list[str] = []
    inc = float(p.get("monthly_income") or 0)
    exp = float(p.get("monthly_expenses") or 0)
    if inc <= 0:
        out.append("monthly_income")
    if exp <= 0:
        out.append("monthly_expenses")
    return out


def missing_for_core_planning(p: dict[str, Any]) -> list[str]:
    """Minimum fields for FIRE, budget, health score, tax (income side)."""
    missing = _missing_money_income_expenses(p)
    if not (p.get("city") or "").strip():
        missing.append("city")
    return list(dict.fromkeys(missing))


def missing_for_tax_detail(p: dict[str, Any]) -> list[str]:
    """Extra fields for meaningful HRA / rent-based calcs (old regime)."""
    base = missing_for_core_planning(p)
    hra = float(p.get("hra") or 0)
    rent = float(p.get("rent_paid") or 0)
    if hra > 0 and rent <= 0:
        base.append("rent_paid")
    return list(dict.fromkeys(base))


def missing_for_money_personality(p: dict[str, Any]) -> list[str]:
    """Personality needs savings behaviour signal."""
    return _missing_money_income_expenses(p)


def humanize_missing(keys: list[str]) -> list[dict[str, str]]:
    rows = []
    for k in keys:
        rows.append({
            "field": k,
            "label": _FIELD_LABELS.get(k, k.replace("_", " ").title()),
            "settings_hint": "Open Settings and save this value — it powers tax, FIRE, and coaching.",
        })
    return rows


def profile_extensions(p: dict[str, Any]) -> dict[str, Any]:
    """Attach to API profile JSON for dashboard and agents."""
    core = missing_for_core_planning(p)
    tax = missing_for_tax_detail(p)
    pers = missing_for_money_personality(p)
    return {
        "profile_gaps_core": core,
        "profile_gaps_tax": tax,
        "profile_gaps_personality": pers,
        "profile_ready_for_fire_budget": len(core) == 0,
        "missing_fields_detail": humanize_missing(list(dict.fromkeys(core + tax))),
    }
