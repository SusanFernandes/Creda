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
