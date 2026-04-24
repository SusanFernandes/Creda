"""
Tax Wizard agent — comprehensive Indian tax analysis.

Features:
  - Old vs New regime comparison (from versioned tax_config)
  - HRA exemption (metro vs non-metro)
  - Full 80C breakdown: ELSS auto-detected from portfolio, EPF, PPF
  - 80D self + parents, 80CCD(1B) NPS, 24(b) home loan
  - LTCG / STCG auto-calculation from portfolio holdings
  - Surcharge for high incomes
  - Advance tax warning (> ₹10K)
  - RAG edge-case verification
  - Missed deduction detection + ranked 80C instruments

Rules source: app.tax_config (version-controlled per FY, updated post-budget).
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState
from app.tax_config import get_tax_rules, compute_tax, TaxYear

logger = logging.getLogger("creda.agents.tax_wizard")

_METRO_CITIES = frozenset([
    "mumbai", "delhi", "kolkata", "chennai",
    "bangalore", "bengaluru", "hyderabad",
])

_TAX_PROMPT = """You are an Indian tax expert for {fy_label}.
Given these calculations, provide:
1. Which regime is better and by how much
2. Missed deductions the user should claim (mention exact section numbers)
3. If capital gains exist, suggest tax-saving strategies (LTCG harvesting, ELSS offset)
4. One actionable step to save more tax next year

Data:
{data}

Be specific with ₹ amounts. Keep it concise — 150 words max."""


# ─── Capital Gains ──────────────────────────────────────────────────────

def _compute_capital_gains(portfolio_funds: list[dict], rules: TaxYear) -> dict:
    """Auto-compute LTCG & STCG from portfolio fund holdings.

    Uses scheme_type to classify equity vs debt.
    Holding period heuristic: if fund has 'xirr' and invested > 0, assume held > 1 year
    for demo (real implementation would use purchase date from CAMS).
    """
    cg = rules.capital_gains
    equity_ltcg = 0.0
    equity_stcg = 0.0
    debt_gains = 0.0
    fund_details = []

    for fund in portfolio_funds:
        invested = fund.get("invested", 0) or 0
        current = fund.get("current_value", 0) or 0
        gain = current - invested
        if gain == 0:
            continue

        scheme_type = (fund.get("scheme_type") or "").lower()
        category = (fund.get("category") or "").lower()
        name = fund.get("fund_name", "Unknown Fund")

        is_equity = scheme_type in ("equity", "elss") or "equity" in category

        # Heuristic: ELSS must be held > 3 years (lock-in), equity funds
        # likely held > 1 year.  For a demo we treat all as long-term.
        # A real implementation would compare purchase_date vs today.
        if is_equity:
            if gain > 0:
                equity_ltcg += gain
                fund_details.append({
                    "fund": name, "type": "Equity LTCG", "gain": round(gain),
                    "rate": f"{cg.equity_ltcg_rate * 100:.1f}%",
                })
            else:
                equity_stcg += gain  # negative = loss
                fund_details.append({
                    "fund": name, "type": "Equity (Loss)", "gain": round(gain),
                    "rate": "offset",
                })
        else:
            # Debt / hybrid — post Apr 2023: no indexation, taxed at slab
            debt_gains += gain
            fund_details.append({
                "fund": name, "type": "Debt/Hybrid (Slab)",
                "gain": round(gain), "rate": "slab rate",
            })

    # Equity LTCG tax (after ₹1.25L exemption)
    net_equity_ltcg = max(equity_ltcg + min(equity_stcg, 0), 0)  # offset losses
    taxable_equity_ltcg = max(net_equity_ltcg - cg.equity_ltcg_exemption, 0)
    equity_ltcg_tax = round(taxable_equity_ltcg * cg.equity_ltcg_rate)

    # Equity STCG tax (losses can carry forward)
    equity_stcg_only = max(-equity_stcg, 0) if equity_stcg < 0 else 0
    equity_stcg_posit = max(equity_stcg, 0)
    equity_stcg_tax = round(equity_stcg_posit * cg.equity_stcg_rate)

    return {
        "equity_ltcg_gross": round(equity_ltcg),
        "equity_stcg_gross": round(max(equity_stcg, 0)),
        "equity_losses": round(min(equity_stcg, 0)),
        "equity_ltcg_exemption": round(min(net_equity_ltcg, cg.equity_ltcg_exemption)),
        "taxable_equity_ltcg": round(taxable_equity_ltcg),
        "equity_ltcg_tax": equity_ltcg_tax,
        "equity_stcg_tax": equity_stcg_tax,
        "debt_gains": round(debt_gains),
        "debt_tax_note": "Taxed at slab rate (no indexation post Apr 2023)",
        "total_cg_tax": equity_ltcg_tax + equity_stcg_tax,
        "fund_details": fund_details[:10],  # cap at 10 for display
    }


# ─── RAG Edge-Case Lookup ──────────────────────────────────────────────

async def _rag_tax_verification(query: str) -> str | None:
    """Query ChromaDB for tax edge-case verification.  Returns None on failure."""
    try:
        from app.config import settings
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_collection("creda_knowledge")
        results = collection.query(query_texts=[query], n_results=3)
        docs = results.get("documents", [[]])[0]
        dists = results.get("distances", [[]])[0]
        relevant = [d for d, dist in zip(docs, dists) if dist < 0.45]
        return "\n".join(relevant) if relevant else None
    except Exception as e:
        logger.debug("RAG tax verification unavailable: %s", e)
        return None


# ─── 80C Breakdown from Portfolio ───────────────────────────────────────

def _detect_80c_from_portfolio(portfolio_funds: list[dict], profile: dict) -> dict:
    """Auto-detect 80C components: ELSS from portfolio, EPF from profile."""
    elss_total = sum(
        f.get("invested", 0) or 0
        for f in portfolio_funds
        if (f.get("scheme_type") or "").lower() == "elss"
    )
    epf_annual = profile.get("epf_balance", 0) * 0.12  # rough: 12% of balance as annual contribution
    ppf_annual = min(profile.get("ppf_balance", 0) * 0.10, 150000)  # rough estimate
    declared_80c = profile.get("investments_80c", 0)

    # Take max of auto-detected vs declared
    auto_total = elss_total + epf_annual + ppf_annual
    effective = max(auto_total, declared_80c)

    return {
        "elss_from_portfolio": round(elss_total),
        "epf_estimated": round(epf_annual),
        "ppf_estimated": round(ppf_annual),
        "declared_80c": round(declared_80c),
        "effective_80c": round(min(effective, 150000)),
    }


# ─── Main Agent ─────────────────────────────────────────────────────────

async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    fy_override = state.get("financial_year")  # allow caller to request specific FY

    rules = get_tax_rules(fy_override)

    monthly_income = float(profile.get("monthly_income") or 0)
    if monthly_income <= 0:
        from app.services.profile_completeness import humanize_missing, missing_for_core_planning
        std_new = rules.new_regime.standard_deduction
        std_old = rules.old_regime.standard_deduction
        zded = {"80C": 0, "80CCD(1B)": 0, "80D": 0, "HRA": 0, "24(b)": 0, "standard": std_old}
        return {
            "needs_input": True,
            "missing_fields_detail": humanize_missing(missing_for_core_planning(profile)),
            "message": "Add your monthly salary/income in Settings first. Then add rent (if claiming HRA), 80C, NPS, and premiums so we can compare regimes on your real numbers — not placeholders.",
            "fy": rules.fy,
            "ay": rules.ay,
            "fy_label": rules.label,
            "gross_income": 0,
            "old_regime": {
                "deductions": zded,
                "total_deductions": std_old,
                "taxable_income": 0,
                "tax": 0,
            },
            "new_regime": {
                "standard_deduction": std_new,
                "employer_nps_deduction": 0,
                "taxable_income": 0,
                "tax": 0,
            },
            "better_regime": "new",
            "savings": 0,
            "breakdown_80c": None,
            "capital_gains": None,
            "advance_tax": None,
            "missed_deductions": [],
            "ranked_80c": [],
            "tax_loss_harvesting": [],
            "rag_insight": None,
            "advice": "",
        }

    income = monthly_income * 12
    age = profile.get("age", 30)
    city = (profile.get("city") or "").strip().lower()

    investments_80c = profile.get("investments_80c", 0)
    nps_80ccd = profile.get("nps_contribution", 0)
    health_premium = profile.get("health_insurance_premium", 0)
    hra = profile.get("hra", 0)
    home_loan_interest = profile.get("home_loan_interest", 0)
    rent_paid = profile.get("rent_paid", 0)

    dl = rules.deductions  # DeductionLimits

    # ── Old Regime Deductions ──
    deduction_80c = min(investments_80c, dl.sec_80c)
    deduction_80ccd = min(nps_80ccd, dl.sec_80ccd_1b)

    # 80D: self + parents
    self_80d_limit = dl.sec_80d_self_senior if age >= 60 else dl.sec_80d_self
    deduction_80d_self = min(health_premium, self_80d_limit)
    parents_premium = profile.get("parents_health_premium", 0)
    parents_senior = profile.get("parents_senior", False)
    parents_80d_limit = dl.sec_80d_parents_senior if parents_senior else dl.sec_80d_parents
    deduction_80d_parents = min(parents_premium, parents_80d_limit)
    deduction_80d = deduction_80d_self + deduction_80d_parents

    # HRA exemption
    basic_salary = income * 0.4
    hra_pct = 0.50 if city in _METRO_CITIES else 0.40
    if hra > 0 and rent_paid > 0:
        deduction_hra = max(min(hra, rent_paid - 0.10 * basic_salary, hra_pct * basic_salary), 0)
    else:
        deduction_hra = 0

    deduction_24b = min(home_loan_interest, dl.sec_24b_self_occupied)
    std_deduction_old = rules.old_regime.standard_deduction

    total_deductions_old = (
        deduction_80c + deduction_80ccd + deduction_80d
        + deduction_hra + deduction_24b + std_deduction_old
    )
    taxable_old = max(income - total_deductions_old, 0)
    tax_old = compute_tax(taxable_old, rules.old_regime, income)

    # ── New Regime ──
    std_deduction_new = rules.new_regime.standard_deduction
    # New regime: employer NPS (80CCD2) is allowed even in new regime
    employer_nps = profile.get("employer_nps", 0)
    taxable_new = max(income - std_deduction_new - employer_nps, 0)
    tax_new = compute_tax(taxable_new, rules.new_regime, income)

    better_regime = "old" if tax_old < tax_new else "new"
    savings = abs(tax_old - tax_new)

    # ── 80C Breakdown (auto-detect from portfolio) ──
    portfolio_funds = (portfolio.get("funds") or []) if portfolio else []
    breakdown_80c = _detect_80c_from_portfolio(portfolio_funds, profile)

    # ── Capital Gains (LTCG/STCG) ──
    capital_gains = _compute_capital_gains(portfolio_funds, rules)

    # ── Advance Tax Warning ──
    max_tax = max(tax_old, tax_new)
    advance_tax = None
    if max_tax > 10000:
        advance_tax = {
            "required": True,
            "estimated_annual": max_tax,
            "schedule": [
                {"quarter": "Q1 (by June 15)", "cumulative_pct": 15, "amount": round(max_tax * 0.15)},
                {"quarter": "Q2 (by Sep 15)", "cumulative_pct": 45, "amount": round(max_tax * 0.30)},
                {"quarter": "Q3 (by Dec 15)", "cumulative_pct": 75, "amount": round(max_tax * 0.30)},
                {"quarter": "Q4 (by Mar 15)", "cumulative_pct": 100, "amount": max_tax - round(max_tax * 0.75)},
            ],
            "note": "Interest u/s 234B/234C applies if advance tax is not paid on time.",
        }

    # ── Missed Deductions ──
    missed = []
    if investments_80c < dl.sec_80c:
        missed.append({"section": "80C", "unused": dl.sec_80c - investments_80c,
                        "suggestion": "ELSS mutual funds, PPF, EPF VPF, or tax-saving FD"})
    if nps_80ccd < dl.sec_80ccd_1b:
        missed.append({"section": "80CCD(1B)", "unused": dl.sec_80ccd_1b - nps_80ccd,
                        "suggestion": "Additional NPS contribution (beyond 80C)"})
    if health_premium == 0:
        missed.append({"section": "80D", "unused": self_80d_limit,
                        "suggestion": f"Health insurance premium (₹{self_80d_limit:,} self, ₹{parents_80d_limit:,} parents)"})
    if home_loan_interest == 0 and profile.get("has_home_loan"):
        missed.append({"section": "24(b)", "unused": dl.sec_24b_self_occupied,
                        "suggestion": "Home loan interest (up to ₹2L for self-occupied)"})

    # ── Ranked 80C Options ──
    ranked_80c = [
        {"instrument": "ELSS Mutual Fund", "lock_in": "3 years", "expected_return": "12-15%",
         "tax_benefit": f"₹{round(dl.sec_80c * 0.30):,}", "liquidity": "Medium",
         "rating": 5, "reason": "Shortest lock-in + equity growth + tax saving"},
        {"instrument": "PPF", "lock_in": "15 years", "expected_return": "7.1%",
         "tax_benefit": f"₹{round(dl.sec_80c * 0.30):,}", "liquidity": "Low",
         "rating": 4, "reason": "EEE tax status — completely tax-free returns"},
        {"instrument": "EPF VPF", "lock_in": "Till retirement", "expected_return": "8.25%",
         "tax_benefit": f"₹{round(dl.sec_80c * 0.30):,}", "liquidity": "Very Low",
         "rating": 4, "reason": "Guaranteed return + employer match"},
        {"instrument": "NPS (80CCD)", "lock_in": "Till 60", "expected_return": "9-12%",
         "tax_benefit": f"₹{round(dl.sec_80ccd_1b * 0.30):,} extra", "liquidity": "Very Low",
         "rating": 3, "reason": "Extra ₹50K deduction beyond 80C"},
        {"instrument": "SCSS", "lock_in": "5 years", "expected_return": "8.2%",
         "tax_benefit": f"₹{round(dl.sec_80c * 0.30):,}", "liquidity": "Low",
         "rating": 3, "reason": "Best for senior citizens — guaranteed"},
        {"instrument": "Tax-Saving FD", "lock_in": "5 years", "expected_return": "6.5-7%",
         "tax_benefit": f"₹{round(dl.sec_80c * 0.30):,}", "liquidity": "Low",
         "rating": 2, "reason": "Safe but interest is fully taxable"},
    ]

    # ── Tax-Loss Harvesting (from portfolio) ──
    tax_loss_harvesting = []
    for fund in portfolio_funds:
        gain = (fund.get("current_value", 0) or 0) - (fund.get("invested", 0) or 0)
        if gain < -1000:
            tax_loss_harvesting.append({
                "fund_name": fund.get("fund_name", "Unknown"),
                "invested": fund.get("invested", 0),
                "current_value": fund.get("current_value", 0),
                "unrealised_loss": round(abs(gain)),
                "potential_tax_saved": round(abs(gain) * rules.capital_gains.equity_ltcg_rate),
                "action": "Redeem to book loss, reinvest in similar category after 30 days",
            })

    # ── RAG Verification (async, non-blocking on failure) ──
    rag_insight = None
    try:
        if missed:
            query = f"Tax deduction sections {', '.join(m['section'] for m in missed)} limits and eligibility for salaried {profile.get('employment_type', 'salaried')} individual in India"
            rag_insight = await _rag_tax_verification(query)
    except Exception:
        pass

    data = {
        "fy": rules.fy,
        "ay": rules.ay,
        "fy_label": rules.label,
        "gross_income": income,
        "old_regime": {
            "deductions": {
                "80C": deduction_80c, "80CCD(1B)": deduction_80ccd,
                "80D": deduction_80d, "HRA": deduction_hra,
                "24(b)": deduction_24b, "standard": std_deduction_old,
            },
            "total_deductions": total_deductions_old,
            "taxable_income": taxable_old,
            "tax": tax_old,
        },
        "new_regime": {
            "standard_deduction": std_deduction_new,
            "employer_nps_deduction": employer_nps,
            "taxable_income": taxable_new,
            "tax": tax_new,
        },
        "better_regime": better_regime,
        "savings": savings,
        "breakdown_80c": breakdown_80c,
        "capital_gains": capital_gains,
        "advance_tax": advance_tax,
        "missed_deductions": missed,
        "ranked_80c": ranked_80c,
        "tax_loss_harvesting": tax_loss_harvesting,
        "rag_insight": rag_insight,
    }

    try:
        result = await primary_llm.ainvoke(_TAX_PROMPT.format(
            fy_label=rules.label, data=str(data)))
        data["advice"] = result.content.strip()
    except Exception:
        data["advice"] = ""

    return data


async def run_tax_wizard(profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns}
    state: FinancialState = {
        "user_id": profile.user_id, "message": "tax analysis", "intent": "tax_wizard",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "tax_wizard", "tax analysis", language, voice_mode)
    return {"analysis": output, "response": response}

