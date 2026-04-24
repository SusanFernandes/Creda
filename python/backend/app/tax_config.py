"""
Versioned Indian Income Tax Rules — single source of truth.

Updated post Union Budget 2025 (announced Feb 2025, effective FY2025-26 / AY2026-27).
When a new budget is announced, copy the latest block and adjust.

Usage:
    from app.tax_config import get_tax_rules
    rules = get_tax_rules("2025-26")
    # rules.new_regime.slabs, rules.old_regime.rebate_limit, etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Slab:
    upto: float       # upper limit of this bracket (use float("inf") for last)
    rate: float        # decimal, e.g. 0.05 for 5%


@dataclass(frozen=True)
class RegimeRules:
    standard_deduction: int
    rebate_limit: int                       # taxable income ≤ this → full rebate
    rebate_max: int                         # max rebate amount (s.87A)
    slabs: tuple[Slab, ...]
    surcharge_thresholds: tuple[tuple[float, float], ...] = ()  # (income_above, rate)
    cess_rate: float = 0.04


@dataclass(frozen=True)
class CapitalGainsRules:
    """Mutual fund capital gains rules."""
    equity_ltcg_holding_months: int = 12
    equity_ltcg_rate: float = 0.125           # 12.5% post Budget 2024
    equity_ltcg_exemption: float = 125000     # ₹1.25L per year
    equity_stcg_rate: float = 0.20            # 20% post Budget 2024
    debt_holding_months: int = 36             # < 36 months = STCG
    debt_stcg_rate: float = 0.0               # taxed at slab (0 = use slab)
    debt_ltcg_rate: float = 0.0               # post Apr 2023: slab rate (no indexation)


@dataclass(frozen=True)
class DeductionLimits:
    sec_80c: int = 150000
    sec_80ccd_1b: int = 50000                # NPS additional
    sec_80ccd_2_pct: float = 0.14            # employer NPS max % of basic
    sec_80d_self: int = 25000
    sec_80d_self_senior: int = 50000
    sec_80d_parents: int = 25000
    sec_80d_parents_senior: int = 50000
    sec_80e: Optional[int] = None            # education loan interest — no limit
    sec_80g_pct: float = 0.50                # 50% of donation (100% for specific funds)
    sec_24b_self_occupied: int = 200000
    sec_24b_let_out: Optional[int] = None    # no limit for let-out


@dataclass(frozen=True)
class TaxYear:
    fy: str                                  # e.g. "2025-26"
    ay: str                                  # e.g. "2026-27"
    label: str
    old_regime: RegimeRules
    new_regime: RegimeRules
    capital_gains: CapitalGainsRules
    deductions: DeductionLimits


# ═══════════════════════════════════════════════════════════════════════════
#  FY 2025-26 (AY 2026-27) — Union Budget 2025
# ═══════════════════════════════════════════════════════════════════════════
FY_2025_26 = TaxYear(
    fy="2025-26",
    ay="2026-27",
    label="FY 2025-26 (Budget 2025)",
    old_regime=RegimeRules(
        standard_deduction=50000,
        rebate_limit=500000,
        rebate_max=12500,
        slabs=(
            Slab(250000, 0.00),
            Slab(500000, 0.05),
            Slab(1000000, 0.20),
            Slab(float("inf"), 0.30),
        ),
        surcharge_thresholds=(
            (5000000, 0.10),
            (10000000, 0.15),
            (20000000, 0.25),
            (50000000, 0.37),
        ),
    ),
    new_regime=RegimeRules(
        standard_deduction=75000,
        rebate_limit=1200000,               # Budget 2025: up from ₹7L
        rebate_max=60000,                    # Budget 2025: up from ₹25K
        slabs=(
            Slab(400000, 0.00),
            Slab(800000, 0.05),
            Slab(1200000, 0.10),
            Slab(1600000, 0.15),
            Slab(2000000, 0.20),
            Slab(2400000, 0.25),
            Slab(float("inf"), 0.30),
        ),
        surcharge_thresholds=(
            (5000000, 0.10),
            (10000000, 0.15),
            (20000000, 0.25),
        ),
    ),
    capital_gains=CapitalGainsRules(
        equity_ltcg_holding_months=12,
        equity_ltcg_rate=0.125,
        equity_ltcg_exemption=125000,
        equity_stcg_rate=0.20,
        debt_holding_months=36,
    ),
    deductions=DeductionLimits(),
)

# ═══════════════════════════════════════════════════════════════════════════
#  FY 2024-25 (AY 2025-26) — legacy / prior year
# ═══════════════════════════════════════════════════════════════════════════
FY_2024_25 = TaxYear(
    fy="2024-25",
    ay="2025-26",
    label="FY 2024-25",
    old_regime=RegimeRules(
        standard_deduction=50000,
        rebate_limit=500000,
        rebate_max=12500,
        slabs=(
            Slab(250000, 0.00),
            Slab(500000, 0.05),
            Slab(1000000, 0.20),
            Slab(float("inf"), 0.30),
        ),
        surcharge_thresholds=(
            (5000000, 0.10),
            (10000000, 0.15),
            (20000000, 0.25),
            (50000000, 0.37),
        ),
    ),
    new_regime=RegimeRules(
        standard_deduction=75000,
        rebate_limit=700000,                 # FY2024-25: ₹7L
        rebate_max=25000,
        slabs=(
            Slab(300000, 0.00),
            Slab(700000, 0.05),
            Slab(1000000, 0.10),
            Slab(1200000, 0.15),
            Slab(1500000, 0.20),
            Slab(float("inf"), 0.30),
        ),
        surcharge_thresholds=(
            (5000000, 0.10),
            (10000000, 0.15),
            (20000000, 0.25),
        ),
    ),
    capital_gains=CapitalGainsRules(
        equity_ltcg_holding_months=12,
        equity_ltcg_rate=0.125,
        equity_ltcg_exemption=125000,
        equity_stcg_rate=0.20,
        debt_holding_months=36,
    ),
    deductions=DeductionLimits(),
)

# ── Registry ────────────────────────────────────────────────────────────
_YEARS: dict[str, TaxYear] = {
    "2025-26": FY_2025_26,
    "2024-25": FY_2024_25,
}

# Default = FY currently in progress
DEFAULT_FY = "2025-26"


def get_tax_rules(fy: str | None = None) -> TaxYear:
    """Return rules for a financial year.  Falls back to DEFAULT_FY."""
    return _YEARS.get(fy or DEFAULT_FY, _YEARS[DEFAULT_FY])


def compute_tax(taxable: float, regime: RegimeRules, gross_income: float = 0) -> float:
    """Compute tax for a given taxable income under the specified regime rules.

    Returns total tax *including* cess and surcharge, but *after* rebate.
    """
    # Slab computation
    raw_tax = 0.0
    prev = 0.0
    for slab in regime.slabs:
        if taxable <= prev:
            break
        bracket = min(taxable, slab.upto) - prev
        raw_tax += bracket * slab.rate
        prev = slab.upto

    # Section 87A rebate
    if taxable <= regime.rebate_limit:
        raw_tax = max(raw_tax - regime.rebate_max, 0)

    # Surcharge (on income, not on tax — but calculated on raw_tax)
    income_for_surcharge = gross_income or taxable
    surcharge_rate = 0.0
    for threshold, rate in regime.surcharge_thresholds:
        if income_for_surcharge > threshold:
            surcharge_rate = rate
    surcharge = raw_tax * surcharge_rate

    # Marginal relief for surcharge (simplified)
    total_before_cess = raw_tax + surcharge

    # Health & Education Cess
    total = round(total_before_cess * (1 + regime.cess_rate))
    return total
