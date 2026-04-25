"""
Portfolio X-Ray agent — CAMS/KFintech PDF parsing, XIRR, overlap, expense drag, benchmarks.
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.portfolio_xray")

_REBALANCE_PROMPT = """You are a mutual fund advisor. Given this portfolio analysis, provide 3 specific rebalancing recommendations.
Focus on: fund consolidation (reduce overlap), expense ratio optimization (switch to direct plans), and asset allocation.

Portfolio data:
{data}

Respond with exactly 3 numbered recommendations. Be specific with fund names and amounts."""


async def run(state: FinancialState) -> dict[str, Any]:
    """Run portfolio X-ray analysis from existing DB data."""
    portfolio = state.get("portfolio_data")
    if not portfolio:
        return {"error": "No portfolio data found. Upload a CAMS statement first."}

    funds = portfolio.get("funds", [])
    if not funds:
        return {"error": "No fund holdings found in portfolio."}

    # Compute aggregates
    total_invested = sum(f.get("invested", 0) for f in funds)
    total_current = sum(f.get("current_value", 0) for f in funds)
    total_gain = total_current - total_invested
    gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0

    # Overlap detection: funds in same category
    from collections import Counter
    cat_counts = Counter(f.get("category", "unknown") for f in funds)
    overlap_categories = {cat: count for cat, count in cat_counts.items() if count > 1}

    # Expense drag: 10-year impact of TER
    expense_drag = sum(
        f.get("current_value", 0) * f.get("expense_ratio", 0) / 100 * 10
        for f in funds
    )

    # Top and bottom performers by XIRR
    sorted_funds = sorted(funds, key=lambda f: f.get("xirr", 0), reverse=True)
    top_3 = sorted_funds[:3]
    bottom_3 = sorted_funds[-3:] if len(sorted_funds) >= 3 else sorted_funds

    analysis = {
        "total_invested": total_invested,
        "current_value": total_current,
        "total_gain": total_gain,
        "gain_pct": round(gain_pct, 2),
        "portfolio_xirr": portfolio.get("xirr", 0),
        "funds_count": len(funds),
        "overlap_categories": overlap_categories,
        "expense_drag_10y": round(expense_drag, 0),
        "top_performers": [{"name": f.get("fund_name"), "xirr": f.get("xirr")} for f in top_3],
        "bottom_performers": [{"name": f.get("fund_name"), "xirr": f.get("xirr")} for f in bottom_3],
    }

    await _enrich_ter_overlap_alpha(state, funds, analysis)

    # Benchmark comparison: Nifty 50 via yfinance
    try:
        benchmark = await _fetch_nifty_benchmark()
        analysis["benchmark"] = benchmark
        portfolio_xirr = portfolio.get("xirr", 0) or 0
        bench_return = benchmark.get("cagr_3y", 0)
        analysis["alpha_vs_nifty"] = round(portfolio_xirr - bench_return, 2)
        analysis["beating_benchmark"] = portfolio_xirr > bench_return
    except Exception as e:
        logger.debug("Benchmark fetch failed: %s", e)
        analysis["benchmark"] = None
        analysis["alpha_vs_nifty"] = None

    # LLM rebalancing recommendations
    try:
        result = await primary_llm.ainvoke(_REBALANCE_PROMPT.format(data=str(analysis)))
        analysis["recommendations"] = result.content.strip()
    except Exception as e:
        logger.warning("LLM rebalancing failed: %s", e)
        analysis["recommendations"] = "Unable to generate recommendations at this time."

    return analysis


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
                invested = sum(t.get("amount", 0) for t in scheme.get("transactions", []) if t.get("amount", 0) > 0)
                current = scheme.get("valuation", {}).get("value", 0)
                units = scheme.get("valuation", {}).get("units", 0)

                # Compute XIRR if we have transactions
                xirr_val = 0
                try:
                    from pyxirr import xirr
                    from datetime import date
                    cashflows = []
                    for t in scheme.get("transactions", []):
                        if t.get("amount") and t.get("date"):
                            cashflows.append((t["date"], -t["amount"]))
                    if cashflows and current > 0:
                        cashflows.append((date.today(), current))
                        dates, amounts = zip(*cashflows)
                        xirr_val = xirr(list(dates), list(amounts)) or 0
                        xirr_val = round(xirr_val * 100, 2)
                except Exception:
                    pass

                # Derive category from scheme name and type
                category = _classify_category(scheme.get("scheme", ""), scheme.get("type", ""))
                # Estimate expense ratio based on plan type
                is_direct = "direct" in scheme.get("scheme", "").lower()
                expense_ratio = _estimate_expense_ratio(category, is_direct)

                funds.append({
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
                })
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


async def _enrich_ter_overlap_alpha(
    state: FinancialState,
    funds: list[dict],
    analysis: dict[str, Any],
) -> None:
    """Attach AMFI TER (DB), holding overlap summary, per-fund alpha vs category benchmark, regular→direct savings."""
    try:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models import FundTer
        from app.core.holdings_db import compute_overlap, fetch_holding_name, get_latest_holdings_month

        isins = [f.get("isin") for f in funds if f.get("isin")]
        ter_map: dict[str, float] = {}
        async with AsyncSessionLocal() as db:
            if isins:
                r = await db.execute(select(FundTer).where(FundTer.isin.in_(isins)))
                for row in r.scalars().all():
                    ter_map[row.isin] = float(row.ter or 0)
            overlaps_raw = (
                await compute_overlap(isins, db) if len(isins) >= 2 else []
            )
            month = await get_latest_holdings_month(db)
            overlap_stocks: list[dict[str, Any]] = []
            for o in overlaps_raw[:12]:
                nm = await fetch_holding_name(db, o["holding_isin"], month)
                overlap_stocks.append({
                    "holding": nm or o["holding_isin"],
                    "fund_a": o["fund_a"],
                    "fund_b": o["fund_b"],
                    "weight_a_pct": round(o["weight_a"] * 100, 1),
                    "weight_b_pct": round(o["weight_b"] * 100, 1),
                })
        analysis["overlap_holdings"] = overlap_stocks
        analysis["overlap_note"] = (
            "Common underlying stocks (AMFI holdings DB) where both funds hold >2% each."
            if overlap_stocks else "No overlap rows (missing ISINs or holdings data)."
        )
    except Exception as e:
        logger.debug("TER/overlap enrich skipped: %s", e)
        analysis["overlap_holdings"] = []
        ter_map = {}

    bench_cache: dict[str, float] = {}

    async def _cagr(sym: str) -> float:
        if sym in bench_cache:
            return bench_cache[sym]
        try:
            import asyncio
            import yfinance as yf
            from datetime import datetime, timedelta

            def _one() -> float:
                t = yf.Ticker(sym)
                h = t.history(period="3y")
                if h is None or len(h) < 50:
                    return 12.0
                cur = float(h["Close"].iloc[-1])
                start = float(h["Close"].iloc[0])
                years = max((h.index[-1] - h.index[0]).days / 365.25, 0.5)
                return ((cur / start) ** (1 / years) - 1) * 100

            v = float(await asyncio.get_event_loop().run_in_executor(None, _one))
        except Exception:
            v = 12.0
        bench_cache[sym] = v
        return v

    nifty_cagr = await _cagr("^NSEI")
    mid_cagr = await _cagr("^CNXMIDCAP")
    cat_bench = {
        "large_cap": nifty_cagr,
        "index": nifty_cagr,
        "elss": nifty_cagr,
        "flexi_cap": nifty_cagr,
        "equity_other": nifty_cagr,
        "mid_cap": mid_cagr,
        "small_cap": mid_cagr,
        "hybrid": nifty_cagr * 0.85,
        "liquid": 6.0,
        "short_debt": 6.5,
    }
    fund_rows = []
    annual_regular_savings = 0.0
    for f in funds:
        isin = f.get("isin") or ""
        cat = (f.get("category") or "equity_other").lower()
        bc = float(cat_bench.get(cat, nifty_cagr))
        xirr = float(f.get("xirr") or 0)
        ter_db = ter_map.get(isin, 0.0)
        ter_use = float(ter_db or f.get("expense_ratio") or 0)
        plan = (f.get("plan_type") or "").lower()
        est_direct_ter = max(0.05, ter_use * 0.45) if plan == "regular" else ter_use
        if plan == "regular" and f.get("current_value"):
            cv = float(f.get("current_value") or 0)
            annual_regular_savings += cv * max(0, (ter_use - est_direct_ter) / 100.0)
        fund_rows.append({
            "fund_name": f.get("fund_name"),
            "current_value": f.get("current_value"),
            "xirr": xirr,
            "benchmark_3y_cagr_pct": round(bc, 2),
            "alpha_vs_benchmark": round(xirr - bc, 2),
            "ter_pct": round(ter_use, 3),
            "plan_type": plan or "unknown",
        })
    analysis["fund_table"] = fund_rows
    analysis["annual_regular_to_direct_savings_estimate"] = round(annual_regular_savings, 0)


async def run_xray_analysis(portfolio, funds, user_id: str) -> dict:
    """Run X-ray on already-loaded portfolio data."""
    funds_data = [
        {c.name: getattr(f, c.name) for c in type(f).__table__.columns}
        for f in funds
    ]
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


async def _fetch_nifty_benchmark() -> dict:
    """Fetch Nifty 50 benchmark returns via yfinance."""
    import asyncio
    def _fetch():
        import yfinance as yf
        from datetime import datetime, timedelta
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="5y")
        if hist.empty:
            return {"available": False}
        current = hist["Close"].iloc[-1]
        # CAGR calculations
        result = {"current_level": round(current, 2), "available": True}
        for years, key in [(1, "cagr_1y"), (3, "cagr_3y"), (5, "cagr_5y")]:
            target_date = datetime.now() - timedelta(days=years * 365)
            past = hist.loc[hist.index >= target_date.strftime("%Y-%m-%d")]
            if not past.empty:
                start_price = past["Close"].iloc[0]
                cagr = ((current / start_price) ** (1 / years) - 1) * 100
                result[key] = round(cagr, 2)
        return result
    return await asyncio.get_event_loop().run_in_executor(None, _fetch)


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
    """Derive fund category from scheme name and type string."""
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
    if any(w in text for w in ["corporate bond", "credit risk", "banking & psu", "debt"]):
        return "corporate_debt"
    if any(w in text for w in ["hybrid", "balanced", "equity savings", "aggressive", "conservative", "dynamic asset"]):
        return "hybrid"
    if any(w in text for w in ["international", "global", "us equity", "nasdaq"]):
        return "international"
    return "equity_other"


def _estimate_expense_ratio(category: str, is_direct: bool) -> float:
    """Estimate TER based on category and plan type (direct vs regular)."""
    # Typical expense ratios for Indian mutual funds (approximate)
    base_ratios = {
        "large_cap": 1.0, "mid_cap": 1.2, "small_cap": 1.4, "flexi_cap": 1.1,
        "elss": 1.1, "index": 0.3, "liquid": 0.25, "short_debt": 0.5,
        "gilt": 0.5, "corporate_debt": 0.6, "hybrid": 1.0, "international": 1.2,
        "equity_other": 1.1,
    }
    base = base_ratios.get(category, 1.0)
    # Direct plans are ~0.5-1% cheaper than regular
    return round(base * 0.4, 2) if is_direct else round(base, 2)
