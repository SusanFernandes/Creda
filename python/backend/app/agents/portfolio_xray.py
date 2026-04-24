"""
Portfolio X-Ray agent — CAMS/KFintech PDF parsing, XIRR, overlap via holdings DB,
TER lookup, benchmark alpha.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.state import FinancialState
from app.core.agent_envelope import wrap_agent_response
from app.core.llm import primary_llm
from app.database import AsyncSessionLocal

logger = logging.getLogger("creda.agents.portfolio_xray")

_REBALANCE_PROMPT = """You are a mutual fund advisor. Given this portfolio analysis, provide 3 specific rebalancing recommendations.
Focus on: fund consolidation (reduce overlap), expense ratio optimization (switch to direct plans), and asset allocation.

Portfolio data:
{data}

Respond with exactly 3 numbered recommendations. Be specific with fund names and amounts."""

BENCHMARK_MAP = {
    "large_cap": "^NSEI",
    "mid_cap": "NIFTY_MIDCAP_150.NS",
    "small_cap": "NIFTY_SMLCAP_250.NS",
    "debt": "NIFTY_10_YR_BENCHMARK.NS",
    "hybrid": "^NSEI",
}


def _estimate_ter_percent(category: str | None, is_direct: bool) -> float:
    """Approximate TER in percent (e.g. 1.0 = 1%) for legacy portfolio_funds rows."""
    cat = category or "equity_other"
    base_ratios = {
        "large_cap": 1.0,
        "mid_cap": 1.2,
        "small_cap": 1.4,
        "flexi_cap": 1.1,
        "elss": 1.1,
        "index": 0.3,
        "liquid": 0.25,
        "short_debt": 0.5,
        "gilt": 0.5,
        "corporate_debt": 0.6,
        "hybrid": 1.0,
        "international": 1.2,
        "equity_other": 1.1,
    }
    base = base_ratios.get(cat, 1.0)
    return round(base * 0.4, 2) if is_direct else round(base, 2)


async def _get_ter(
    db, isin: str, category: str | None, plan_is_direct: bool
) -> tuple[float, str, str]:
    from sqlalchemy import select

    from app.models import FundTer

    if not isin:
        ter = _estimate_ter_percent(category, plan_is_direct) / 100.0
        return ter, "estimated", "regular"
    r = await db.execute(select(FundTer).where(FundTer.isin == isin))
    row = r.scalar_one_or_none()
    if row and row.ter is not None:
        pt = (row.plan_type or "regular").lower()
        return float(row.ter), "live", pt
    ter = _estimate_ter_percent(category, plan_is_direct) / 100.0
    return ter, "estimated", "direct" if plan_is_direct else "regular"


def _benchmark_cagr_sync(symbol: str, years: int = 5) -> float | None:
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        hist = t.history(period=f"{years}y")
        if hist is None or hist.empty or len(hist) < 50:
            return None
        close = hist["Close"].dropna()
        if len(close) < 2:
            return None
        first = float(close.iloc[0])
        last = float(close.iloc[-1])
        if first <= 0:
            return None
        return float((last / first) ** (1.0 / years) - 1.0)
    except Exception:
        return None


async def run(state: FinancialState) -> dict[str, Any]:
    from app.agents.profile_checks import require_complete_profile

    inc = require_complete_profile(state)
    if inc:
        return inc

    portfolio = state.get("portfolio_data")
    user_id = state.get("user_id", "")
    if not portfolio:
        raw = wrap_agent_response(
            "portfolio_xray",
            "error",
            "partial",
            {},
            {"error": "No portfolio data found. Upload a CAMS statement first."},
        )
        raw["status"] = "error"
        return raw

    funds_in = portfolio.get("funds", [])
    if not funds_in:
        raw = wrap_agent_response(
            "portfolio_xray",
            "error",
            "partial",
            {},
            {"error": "No fund holdings found in portfolio."},
        )
        raw["status"] = "error"
        return raw

    async with AsyncSessionLocal() as db:
        from app.core.holdings_db import compute_overlap, fetch_holding_name, get_latest_holdings_month

        isins = [f.get("isin") or "" for f in funds_in]
        overlaps_raw = await compute_overlap(isins, db)
        month = await get_latest_holdings_month(db)

        enriched_funds = []
        total_ter_cost = 0.0
        any_estimated_ter = False
        portfolio_xirr = portfolio.get("xirr") or 0

        for f in funds_in:
            name = f.get("fund_name", "")
            isin = f.get("isin") or ""
            cat = f.get("category") or "large_cap"
            plan = (f.get("plan_type") or "").lower()
            is_direct = plan == "direct"
            cv = float(f.get("current_value") or 0)
            invested = float(f.get("invested") or 0)
            fxirr = float(f.get("xirr") or 0) / 100.0 if f.get("xirr") else 0.0

            ter, ter_src, plan_type = await _get_ter(db, isin, cat, is_direct)
            if ter_src == "estimated":
                any_estimated_ter = True
            annual_ter_cost = cv * float(ter or 0)
            total_ter_cost += annual_ter_cost

            bench_sym = BENCHMARK_MAP.get(cat, "^NSEI")
            bench_cagr = await asyncio.to_thread(_benchmark_cagr_sync, bench_sym, 5)
            if bench_cagr is None:
                bench_cagr = 0.12
            alpha = fxirr - bench_cagr
            alpha_label = f"{alpha * 100:+.1f}%"

            enriched_funds.append(
                {
                    "name": name,
                    "isin": isin,
                    "xirr": round(float(f.get("xirr") or 0), 2),
                    "current_value": round(cv),
                    "invested_value": round(invested),
                    "gain_pct": round((cv - invested) / invested * 100, 1) if invested > 0 else 0,
                    "ter": ter,
                    "ter_source": ter_src,
                    "plan_type": plan_type,
                    "category": cat,
                    "benchmark": bench_sym,
                    "benchmark_cagr": round(bench_cagr * 100, 2),
                    "alpha": round(alpha * 100, 2),
                    "alpha_label": alpha_label,
                    "annual_ter_cost_rs": round(annual_ter_cost),
                }
            )

        overlaps_out = []
        for o in overlaps_raw:
            hname = await fetch_holding_name(db, o["holding_isin"], month)
            overlaps_out.append(
                {
                    "fund_a": o["fund_a"],
                    "fund_b": o["fund_b"],
                    "holding": hname or o["holding_isin"],
                    "weight_a": round(o["weight_a"], 4),
                    "weight_b": round(o["weight_b"], 4),
                }
            )

    total_invested = sum(f.get("invested_value", 0) for f in enriched_funds)
    total_current = sum(f.get("current_value", 0) for f in enriched_funds)
    gain_pct = (
        (total_current - total_invested) / total_invested * 100 if total_invested > 0 else 0
    )

    direct_switch_saving = round(total_ter_cost * 0.35)

    analysis_inner = {
        "overall_xirr": portfolio_xirr,
        "funds": enriched_funds,
        "overlaps": overlaps_out,
        "total_annual_ter_cost": round(total_ter_cost),
        "direct_switch_annual_saving": direct_switch_saving,
        "rebalancing": [],
        "total_invested": total_invested,
        "total_current": total_current,
        "gain_pct": round(gain_pct, 2),
    }

    try:
        result = await primary_llm.ainvoke(_REBALANCE_PROMPT.format(data=str(analysis_inner)))
        analysis_inner["recommendations_text"] = result.content.strip()
    except Exception as e:
        logger.warning("LLM rebalancing failed: %s", e)
        analysis_inner["recommendations_text"] = "Unable to generate recommendations at this time."

    dq = "live"
    if any_estimated_ter:
        dq = "estimated"
    if not isins or not any(isins):
        dq = "estimated"

    out = wrap_agent_response(
        "portfolio_xray",
        "success",
        dq,
        {"data_source": "cams_upload"},
        analysis_inner,
    )
    out["data_quality"] = dq
    return out


async def parse_cams_statement(pdf_bytes: bytes, password: str | None = None) -> dict:
    """Parse CAMS/KFintech PDF using casparser."""
    import casparser
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        data = casparser.read_cas_pdf(tmp_path, password=password or "")
        funds = []
        total_invested = 0
        total_current = 0

        for folio in data.get("folios", []):
            for scheme in folio.get("schemes", []):
                invested = sum(
                    t.get("amount", 0) for t in scheme.get("transactions", []) if t.get("amount", 0) > 0
                )
                current = scheme.get("valuation", {}).get("value", 0)
                units = scheme.get("valuation", {}).get("units", 0)

                xirr_val = 0
                try:
                    from pyxirr import xirr
                    from datetime import date as date_cls

                    cashflows = []
                    for t in scheme.get("transactions", []):
                        if t.get("amount") and t.get("date"):
                            cashflows.append((t["date"], -t["amount"]))
                    if cashflows and current > 0:
                        cashflows.append((date_cls.today(), current))
                        dates, amounts = zip(*cashflows)
                        xv = xirr(list(dates), list(amounts)) or 0
                        xirr_val = round(xv * 100, 2)
                except Exception:
                    pass

                category = _classify_category(scheme.get("scheme", ""), scheme.get("type", ""))
                is_direct = "direct" in scheme.get("scheme", "").lower()
                expense_ratio = _estimate_ter_percent(category, is_direct)
                raw_isin = scheme.get("isin") or scheme.get("isin1") or ""

                funds.append(
                    {
                        "fund_name": scheme.get("scheme", ""),
                        "amc": scheme.get("amc", folio.get("amc", "")),
                        "scheme_type": _classify_scheme(scheme.get("scheme", "")),
                        "category": category,
                        "plan_type": "direct" if is_direct else "regular",
                        "invested": invested,
                        "current_value": current,
                        "units": units,
                        "xirr": xirr_val,
                        "expense_ratio": expense_ratio,
                        "isin": str(raw_isin).strip(),
                    }
                )
                total_invested += invested
                total_current += current

        return {
            "total_invested": total_invested,
            "current_value": total_current,
            "xirr": 0,
            "funds": funds,
        }
    finally:
        os.unlink(tmp_path)


async def run_xray_analysis(portfolio, funds, user_id: str) -> dict:
    """Run X-ray on already-loaded portfolio data."""
    funds_data = [{c.name: getattr(f, c.name) for c in type(f).__table__.columns} for f in funds]
    state: FinancialState = {
        "user_id": user_id,
        "message": "portfolio xray",
        "intent": "portfolio_xray",
        "language": "en",
        "voice_mode": False,
        "history": [],
        "portfolio_data": {
            "total_invested": portfolio.total_invested,
            "current_value": portfolio.current_value,
            "xirr": portfolio.xirr,
            "funds": funds_data,
        },
    }
    return await run(state)


def _classify_scheme(name: str) -> str:
    name_lower = name.lower()
    if "elss" in name_lower or "tax" in name_lower:
        return "elss"
    if "debt" in name_lower or "bond" in name_lower or "liquid" in name_lower:
        return "debt"
    if "hybrid" in name_lower or "balanced" in name_lower:
        return "hybrid"
    return "equity"


def _classify_category(name: str, scheme_type: str = "") -> str:
    text = f"{name} {scheme_type}".lower()
    if any(w in text for w in ["large cap", "largecap", "large & mid", "bluechip", "nifty 50", "sensex"]):
        return "large_cap"
    if any(w in text for w in ["mid cap", "midcap"]):
        return "mid_cap"
    if any(w in text for w in ["small cap", "smallcap"]):
        return "small_cap"
    if any(w in text for w in ["flexi", "multi cap", "multicap", "focused"]):
        return "flexi_cap"
    if any(w in text for w in ["elss", "tax sav"]):
        return "elss"
    if any(w in text for w in ["index", "nifty", "sensex", "etf"]):
        return "index"
    if any(w in text for w in ["liquid", "money market", "overnight"]):
        return "liquid"
    if any(w in text for w in ["short duration", "ultra short", "low duration"]):
        return "short_debt"
    if any(w in text for w in ["gilt", "government", "gsec"]):
        return "gilt"
    if any(
        w in text
        for w in ["corporate bond", "credit risk", "banking & psu", "debt"]
    ):
        return "corporate_debt"
    if any(
        w in text
        for w in ["hybrid", "balanced", "equity savings", "aggressive", "conservative", "dynamic asset"]
    ):
        return "hybrid"
    if any(w in text for w in ["international", "global", "us equity", "nasdaq"]):
        return "international"
    return "equity_other"

