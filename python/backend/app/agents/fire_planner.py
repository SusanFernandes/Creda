"""
FIRE Planner agent — Financial Independence Retire Early.
Computes FIRE number, required SIP, roadmap, sensitivity vs returns, tax/insurance gaps.
Uses UserAssumptions (inflation, returns, SIP step-up) + portfolio-weighted nominal return when available.
"""
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState
from app.database import AsyncSessionLocal

_FIRE_PROMPT = """You are a FIRE (Financial Independence Retire Early) expert for Indian investors.
Given the calculations below, provide a concise FIRE plan with:
1. Whether the user is on track or behind
2. Key actions to accelerate FIRE (max 3)
3. Tax-saving opportunities they're missing
4. Insurance gaps

Data:
{data}

Be specific with ₹ amounts and timelines."""


def _blended_nominal_return(
    portfolio_funds: list[dict],
    assumptions: dict[str, Any],
    profile: dict[str, Any],
) -> float:
    """Weight liquid funds by current_value; fallback to risk-based single return."""
    lc = float(assumptions.get("equity_lc_return") or 0.12)
    mc = float(assumptions.get("equity_mc_return") or 0.14)
    sc = float(assumptions.get("equity_sc_return") or 0.16)
    debt = float(assumptions.get("debt_return") or 0.07)

    funds = portfolio_funds or []
    total = sum(float(f.get("current_value") or 0) for f in funds)
    if total <= 0:
        rt = (profile.get("risk_tolerance") or profile.get("risk_appetite") or "moderate").lower()
        if rt == "conservative":
            return max(0.04, (lc + debt) / 2 * 0.65 + debt * 0.35)
        if rt == "aggressive":
            return min(0.18, (lc + sc) / 2)
        return lc

    wsum = 0.0
    for f in funds:
        cv = float(f.get("current_value") or 0)
        if cv <= 0:
            continue
        w = cv / total
        cat = (f.get("category") or "").lower()
        st = (f.get("scheme_type") or "").lower()
        if "debt" in cat or "liquid" in cat or st == "debt":
            r = debt
        elif "small" in cat:
            r = sc
        elif "mid" in cat:
            r = mc
        else:
            r = lc
        wsum += w * r
    return max(0.04, min(0.20, wsum))


def _required_sip_for_real_return(
    fire_number: float,
    current_corpus: float,
    years_to_fire: int,
    real_annual: float,
    monthly_return: float,
) -> tuple[float, float]:
    """Return (required_monthly_sip, fv_current_corpus_at_retirement)."""
    months = max(years_to_fire * 12, 1)
    if monthly_return <= 0 or years_to_fire <= 0:
        return 0.0, current_corpus
    fv_current = current_corpus * ((1 + real_annual) ** years_to_fire)
    gap = max(fire_number - fv_current, 0)
    if gap <= 0:
        return 0.0, fv_current
    denom = ((1 + monthly_return) ** months) - 1
    if denom <= 0:
        return 0.0, fv_current
    req = gap * monthly_return / denom
    return req, fv_current


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}

    income = float(profile.get("monthly_income") or 0)
    expenses = float(profile.get("monthly_expenses") or 0)
    age = int(profile.get("age") or 0)
    fire_target_age = int(profile.get("fire_target_age") or 0)

    if income <= 0 or expenses <= 0 or age <= 0 or fire_target_age <= 0 or fire_target_age <= age:
        from app.services.profile_completeness import humanize_missing, missing_for_core_planning
        miss = list(missing_for_core_planning(profile))
        if age <= 0 and "age" not in miss:
            miss.append("age")
        if (fire_target_age <= 0 or fire_target_age <= age) and "fire_target_age" not in miss:
            miss.append("fire_target_age")
        return {
            "input_required": True,
            "missing_fields_detail": humanize_missing(list(dict.fromkeys(miss))),
            "message": "FIRE needs your real monthly income, monthly expenses, age, and a target retirement age after your current age — all saved in Settings. We do not fabricate these numbers.",
        }

    async with AsyncSessionLocal() as db:
        from app.core.assumptions import get_user_assumptions

        assumptions = await get_user_assumptions(db, state["user_id"])

    inflation_rate = float(assumptions.get("inflation_rate") or 0.06)
    sip_step_up = float(assumptions.get("sip_stepup_pct") or 0.10)

    portfolio = state.get("portfolio_data") or {}
    funds = portfolio.get("funds") or []
    nominal_base = _blended_nominal_return(funds, assumptions, profile)
    real_return_base = max(0.005, nominal_base - inflation_rate)
    monthly_return_base = real_return_base / 12

    savings = float(profile.get("savings") or 0)
    epf = float(profile.get("epf_balance") or 0)
    nps = float(profile.get("nps_balance") or 0)
    ppf = float(profile.get("ppf_balance") or 0)

    annual_expenses = expenses * 12
    years_to_fire = max(fire_target_age - age, 1)
    future_annual_expenses = annual_expenses * ((1 + inflation_rate) ** years_to_fire)
    fire_number = future_annual_expenses / 0.04

    current_corpus = float(portfolio.get("current_value") or 0) + savings + epf + nps + ppf

    emi = float(profile.get("monthly_emi") or 0)
    surplus = max(0.0, income - expenses - emi)
    explicit_sip = float(profile.get("monthly_sip_contribution") or 0)
    if explicit_sip > 0:
        current_sip = explicit_sip
        sip_basis = "monthly_sip_contribution from profile (explicit SIP)"
    else:
        current_sip = surplus
        sip_basis = "monthly_income minus monthly_expenses minus monthly_emi (investable surplus)"

    required_sip, fv_current = _required_sip_for_real_return(
        fire_number, current_corpus, years_to_fire, real_return_base, monthly_return_base,
    )
    sip_gap = max(required_sip - current_sip, 0)

    roadmap = []
    projected_corpus = current_corpus
    annual_sip = current_sip * 12
    for year in range(1, min(years_to_fire + 1, 31)):
        projected_corpus = projected_corpus * (1 + real_return_base) + annual_sip
        roadmap.append({
            "year": year,
            "age": age + year,
            "corpus": round(projected_corpus),
            "annual_sip": round(annual_sip),
        })
        annual_sip *= 1 + sip_step_up

    monthly_roadmap = []
    proj = current_corpus
    monthly_sip_amount = current_sip
    mr = monthly_return_base
    for month in range(1, min(years_to_fire * 12 + 1, 37)):
        proj = proj * (1 + mr) + monthly_sip_amount
        if month % 12 == 0:
            monthly_sip_amount *= 1 + sip_step_up
        monthly_roadmap.append({
            "month": month,
            "corpus": round(proj),
            "sip": round(monthly_sip_amount),
        })

    glide_path = []
    for year in range(0, min(years_to_fire + 1, 31)):
        remaining_years = years_to_fire - year
        if remaining_years >= 15:
            equity_pct = 80
        elif remaining_years >= 10:
            equity_pct = 70
        elif remaining_years >= 5:
            equity_pct = 60
        elif remaining_years >= 3:
            equity_pct = 45
        elif remaining_years >= 1:
            equity_pct = 30
        else:
            equity_pct = 20
        glide_path.append({
            "year": year,
            "age": age + year,
            "equity_pct": equity_pct,
            "debt_pct": 100 - equity_pct,
            "phase": "accumulation" if remaining_years > 5 else "transition" if remaining_years > 1 else "preservation",
        })

    investments_80c = float(profile.get("investments_80c") or profile.get("section_80c_amount") or 0)
    nps_contribution = float(profile.get("nps_contribution") or 0)
    tax_gaps = []
    if investments_80c < 150000:
        tax_gaps.append(f"80C: ₹{150000 - investments_80c:,.0f} unused of ₹1.5L limit")
    if nps_contribution < 50000:
        tax_gaps.append(f"80CCD(1B): ₹{50000 - nps_contribution:,.0f} additional NPS deduction available")
    if not profile.get("has_health_insurance"):
        tax_gaps.append("80D: No health insurance — missing ₹25,000 deduction + health coverage")

    insurance_gaps = []
    life_cover = float(profile.get("life_insurance_cover") or 0)
    recommended_cover = income * 12 * 15
    if life_cover < recommended_cover:
        insurance_gaps.append(
            f"Term life: ₹{(recommended_cover - life_cover):,.0f} additional cover needed (target: 15x annual income)"
        )

    sensitivity = []
    for label, delta in (("conservative", -0.02), ("base", 0.0), ("optimistic", 0.02)):
        nom = max(0.04, min(0.22, nominal_base + delta))
        real_r = max(0.005, nom - inflation_rate)
        mr = real_r / 12
        req, fv_c = _required_sip_for_real_return(fire_number, current_corpus, years_to_fire, real_r, mr)
        proj_ret = age + years_to_fire
        sensitivity.append({
            "label": label,
            "nominal_return_pct": round(nom * 100, 1),
            "real_return_pct": round(real_r * 100, 2),
            "required_monthly_sip": round(req),
            "corpus_at_target_age_if_no_extra_sip": round(fv_c),
            "retirement_calendar_year": None,
            "projected_age_at_target": proj_ret,
        })

    data = {
        "fire_number": round(fire_number),
        "current_corpus": round(current_corpus),
        "gap": round(max(fire_number - fv_current, 0)),
        "years_to_fire": years_to_fire,
        "target_age": fire_target_age,
        "required_sip": round(required_sip),
        "current_sip": round(current_sip, 2),
        "sip_basis": sip_basis,
        "sip_gap": round(sip_gap),
        "on_track": required_sip <= current_sip,
        "roadmap_summary": roadmap[:5],
        "roadmap": roadmap,
        "monthly_roadmap": monthly_roadmap,
        "glide_path": glide_path,
        "tax_gaps": tax_gaps,
        "insurance_gaps": insurance_gaps,
        "sensitivity": sensitivity,
        "assumptions_used": {
            "inflation_rate_pct": round(inflation_rate * 100, 2),
            "nominal_return_assumed_pct": round(nominal_base * 100, 2),
            "real_return_used_pct": round(real_return_base * 100, 2),
            "sip_step_up_pct": round(sip_step_up * 100, 2),
            "portfolio_blended_nominal": bool(funds),
        },
        "step_up_note": (
            f"Annual SIP step-up of {sip_step_up * 100:.0f}% is applied in the roadmap; "
            "adjust in Settings → Assumptions."
        ),
    }

    try:
        result = await primary_llm.ainvoke(_FIRE_PROMPT.format(data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_fire_planner(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "FIRE plan", "intent": "fire_planner",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "fire_planner", "FIRE plan", language, voice_mode)
    return {"analysis": output, "response": response}
