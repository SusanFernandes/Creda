"""
Portfolio X-Ray Agent — Core ET PS9 feature.
Parses CAMS/KFintech PDFs, computes true XIRR, detects overlap, calculates expense drag,
and generates LLM-powered rebalancing recommendations.
"""

from __future__ import annotations
import logging
import tempfile
import os
from datetime import date, datetime
from typing import Dict, List, Any

from langchain_groq import ChatGroq
from agents.state import FinancialState

logger = logging.getLogger(__name__)

# ─── PDF Parsing ──────────────────────────────────────────────────────────────

def parse_cams_pdf(pdf_bytes: bytes, password: str) -> dict:
    """Parse CAMS/KFintech PDF using casparser (MIT)."""
    import casparser

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name
    try:
        data = casparser.read_cas_pdf(tmp_path, password)
        return data
    finally:
        os.unlink(tmp_path)


# ─── XIRR Computation ────────────────────────────────────────────────────────

def compute_portfolio_xirr(cas_data: dict) -> dict:
    """Compute true XIRR per scheme and overall using pyxirr (Rust, MIT)."""
    from pyxirr import xirr as calculate_xirr

    results: List[Dict[str, Any]] = []
    all_dates: list = []
    all_amounts: list = []

    for folio in cas_data.get("folios", []):
        for scheme in folio.get("schemes", []):
            s_dates: list = []
            s_amounts: list = []

            for txn in scheme.get("transactions", []):
                try:
                    txn_date = datetime.strptime(txn["date"], "%Y-%m-%d").date()
                except (KeyError, ValueError):
                    continue
                amount = float(txn.get("amount", 0))
                txn_type = txn.get("type", "").lower()

                if txn_type in ("purchase", "sip", "switch_in"):
                    s_dates.append(txn_date)
                    s_amounts.append(-abs(amount))
                elif txn_type in ("redemption", "switch_out"):
                    s_dates.append(txn_date)
                    s_amounts.append(abs(amount))

                all_dates.append(s_dates[-1] if s_dates else txn_date)
                all_amounts.append(s_amounts[-1] if s_amounts else 0)

            current_value = float(scheme.get("valuation", {}).get("value", 0) or 0)
            scheme_xirr_pct = None
            if current_value and s_dates:
                s_dates.append(date.today())
                s_amounts.append(current_value)
                try:
                    scheme_xirr_pct = round(calculate_xirr(s_dates, s_amounts) * 100, 2)
                except Exception:
                    scheme_xirr_pct = None

            results.append({
                "scheme": scheme.get("scheme", "Unknown"),
                "isin": scheme.get("isin", ""),
                "amfi_code": scheme.get("amfi", ""),
                "invested_value": sum(abs(a) for a in s_amounts if a < 0),
                "current_value": current_value,
                "xirr": scheme_xirr_pct,
                "transactions_count": len(scheme.get("transactions", [])),
                "close_units": scheme.get("close", 0),
                "nav": scheme.get("valuation", {}).get("nav", 0),
                "amc": folio.get("amc", ""),
            })

    # Overall XIRR
    overall_xirr_pct = None
    try:
        total_current = sum(r["current_value"] for r in results)
        if all_dates:
            all_dates.append(date.today())
            all_amounts.append(total_current)
            xirr_val = calculate_xirr(all_dates, all_amounts)
            overall_xirr_pct = round(xirr_val * 100, 2) if xirr_val is not None else None
    except Exception:
        pass

    return {
        "schemes": results,
        "overall_xirr": overall_xirr_pct,
        "total_invested": sum(r["invested_value"] for r in results),
        "total_current_value": sum(r["current_value"] for r in results),
    }


# ─── Overlap Analysis ────────────────────────────────────────────────────────

_CATEGORIES = {
    "large cap": ["large cap", "bluechip", "top 100", "nifty 50"],
    "mid cap": ["mid cap", "midcap", "nifty midcap"],
    "small cap": ["small cap", "smallcap"],
    "flexi cap": ["flexi cap", "flexicap", "multi cap", "multicap"],
    "elss": ["elss", "tax saver", "tax saving"],
    "debt": ["debt", "liquid", "overnight", "ultra short", "short duration", "bond", "gilt"],
    "hybrid": ["hybrid", "balanced", "aggressive hybrid", "conservative hybrid"],
    "index": ["index", "nifty", "sensex", "passive"],
}


def _detect_category(scheme_name: str) -> str:
    name_lower = scheme_name.lower()
    for cat, kws in _CATEGORIES.items():
        if any(kw in name_lower for kw in kws):
            return cat
    return "other"


def compute_portfolio_overlap(schemes: list) -> dict:
    category_map: Dict[str, List[str]] = {}
    overlaps = []

    for s in schemes:
        cat = _detect_category(s["scheme"])
        s["detected_category"] = cat
        category_map.setdefault(cat, []).append(s["scheme"])

    for cat, funds in category_map.items():
        if len(funds) >= 2 and cat not in ("debt", "other"):
            overlaps.append({
                "category": cat,
                "duplicate_funds": funds,
                "recommendation": f"You have {len(funds)} funds in {cat}. Consider consolidating to 1.",
                "severity": "high" if len(funds) >= 3 else "medium",
            })

    return {
        "overlaps": overlaps,
        "category_distribution": {k: len(v) for k, v in category_map.items()},
        "overlap_count": len(overlaps),
    }


# ─── Expense Drag ────────────────────────────────────────────────────────────

_TYPICAL_ER = {
    "index": 0.10, "large cap": 1.20, "mid cap": 1.50, "small cap": 1.70,
    "elss": 1.50, "flexi cap": 1.40, "debt": 0.50, "hybrid": 1.30, "other": 1.50,
}

# ─── Benchmark Comparison via yfinance ────────────────────────────────────────

_BENCHMARK_TICKERS = {
    "large cap": "^NSEI",          # Nifty 50
    "mid cap": "NIFTYMIDCAP150.NS",  # Nifty Midcap 150
    "small cap": "NIFTYSMLCAP250.NS",  # Nifty Smallcap 250
    "flexi cap": "^NSEI",         # Nifty 50 as proxy
    "elss": "^NSEI",              # Nifty 50 as proxy
    "debt": "0P00017LCT.BO",     # CRISIL Composite Bond Index proxy
    "hybrid": "^NSEI",            # Nifty 50 as proxy
    "index": "^NSEI",
    "other": "^NSEI",
}


def compute_benchmark_comparison(schemes: list) -> dict:
    """Compare scheme performance against relevant market benchmarks using yfinance."""
    import yfinance as yf
    from datetime import timedelta

    comparisons = []
    benchmarks_fetched: Dict[str, float] = {}
    end_date = date.today()
    start_1y = end_date - timedelta(days=365)
    start_3y = end_date - timedelta(days=365 * 3)

    for ticker_key in set(s.get("detected_category", "other") for s in schemes):
        ticker = _BENCHMARK_TICKERS.get(ticker_key, "^NSEI")
        if ticker in benchmarks_fetched:
            continue
        try:
            data = yf.download(ticker, start=start_3y.isoformat(), end=end_date.isoformat(),
                               progress=False, auto_adjust=True)
            if data is not None and len(data) > 20:
                close = data["Close"]
                price_now = float(close.iloc[-1])
                # 1-year return
                mask_1y = close.index >= str(start_1y)
                ret_1y = None
                if mask_1y.any():
                    price_1y = float(close[mask_1y].iloc[0])
                    ret_1y = round((price_now / price_1y - 1) * 100, 2)
                # 3-year CAGR
                price_3y = float(close.iloc[0])
                years_held = (close.index[-1] - close.index[0]).days / 365.25
                ret_3y_cagr = round(((price_now / price_3y) ** (1 / max(years_held, 0.5)) - 1) * 100, 2)

                benchmarks_fetched[ticker] = ret_1y
                benchmarks_fetched[f"{ticker}_3y"] = ret_3y_cagr
        except Exception as e:
            logger.warning("Benchmark fetch failed for %s: %s", ticker, e)

    for s in schemes:
        cat = s.get("detected_category", "other")
        ticker = _BENCHMARK_TICKERS.get(cat, "^NSEI")
        bm_1y = benchmarks_fetched.get(ticker)
        bm_3y = benchmarks_fetched.get(f"{ticker}_3y")
        scheme_xirr = s.get("xirr")

        alpha = round(scheme_xirr - bm_1y, 2) if scheme_xirr is not None and bm_1y is not None else None
        comparisons.append({
            "scheme": s["scheme"],
            "category": cat,
            "scheme_xirr": scheme_xirr,
            "benchmark_ticker": ticker,
            "benchmark_1yr_return": bm_1y,
            "benchmark_3yr_cagr": bm_3y,
            "alpha_vs_benchmark": alpha,
            "verdict": (
                "outperforming" if alpha and alpha > 1
                else "market-matching" if alpha and -1 <= alpha <= 1
                else "underperforming" if alpha and alpha < -1
                else "insufficient data"
            ),
        })

    return {
        "scheme_vs_benchmark": comparisons,
        "outperforming_count": sum(1 for c in comparisons if c["verdict"] == "outperforming"),
        "underperforming_count": sum(1 for c in comparisons if c["verdict"] == "underperforming"),
        "benchmarks_used": list(set(c["benchmark_ticker"] for c in comparisons)),
    }


def compute_expense_drag(schemes: list) -> dict:
    total_value = sum(s["current_value"] for s in schemes)
    total_annual_cost = 0.0
    breakdown = []

    for s in schemes:
        cat = s.get("detected_category", "other")
        er_pct = _TYPICAL_ER.get(cat, 1.5)
        annual_cost = s["current_value"] * er_pct / 100
        total_annual_cost += annual_cost
        is_regular = "regular" in s["scheme"].lower()

        breakdown.append({
            "scheme": s["scheme"],
            "category": cat,
            "estimated_er_percent": er_pct,
            "annual_cost_inr": round(annual_cost, 2),
            "is_regular_plan": is_regular,
            "switch_to_direct_savings": round(annual_cost * 0.5, 2) if is_regular else 0,
        })

    return {
        "total_annual_expense_inr": round(total_annual_cost, 2),
        "effective_expense_ratio": round(total_annual_cost / total_value * 100, 3) if total_value else 0,
        "10yr_drag_inr": round(total_annual_cost * 10 * 1.12, 2),
        "scheme_breakdown": breakdown,
        "regular_plan_count": sum(1 for b in breakdown if b["is_regular_plan"]),
    }


# ─── Rebalancing via LLM ─────────────────────────────────────────────────────

def generate_rebalancing_plan(xray: dict, user_profile: dict) -> dict:
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    schemes_summary = "\n".join(
        f"- {s['scheme']}: XIRR {s['xirr']}%, Value ₹{s['current_value']:,.0f}, "
        f"Category {s.get('detected_category', '?')}"
        for s in xray["schemes"][:12]
    )
    prompt = f"""You are a SEBI-registered financial advisor analysing an Indian investor's mutual fund portfolio.

PORTFOLIO:
- Total Invested: ₹{xray['total_invested']:,.0f}
- Current Value: ₹{xray['total_current_value']:,.0f}
- True XIRR: {xray['overall_xirr']}%
- Overlaps: {xray['overlap_analysis']['overlap_count']}
- Annual expense drag: ₹{xray['expense_drag']['total_annual_expense_inr']:,.0f}
- Benchmark: {xray.get('benchmark_comparison', {}).get('outperforming_count', '?')} funds outperforming, {xray.get('benchmark_comparison', {}).get('underperforming_count', '?')} underperforming

FUNDS:
{schemes_summary}

USER: Age {user_profile.get('age','?')}, Risk {user_profile.get('risk_tolerance',3)}/5, Goal {user_profile.get('goal_type','growth')}, Horizon {user_profile.get('time_horizon',10)}yr

Give EXACTLY 3 actionable rebalancing recommendations.
Format: 1. [ACTION] [FUND] → [REASON] → [EXPECTED IMPACT]
Keep each under 30 words. Be specific with ₹ amounts where possible."""

    resp = llm.invoke(prompt)
    return {"recommendations": resp.content, "generated_at": datetime.utcnow().isoformat()}


# ─── Agent Node ───────────────────────────────────────────────────────────────

def portfolio_xray_agent(state: FinancialState) -> dict:
    """LangGraph node — runs the full portfolio X-Ray pipeline."""
    portfolio = state.get("portfolio_data", {})
    user_profile = state.get("user_profile", {})

    if not portfolio.get("schemes"):
        return {
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                "portfolio_xray": {"error": "No portfolio data. Please upload a CAMS PDF."},
            }
        }

    schemes = portfolio["schemes"]
    overlap = compute_portfolio_overlap(schemes)
    expense = compute_expense_drag(schemes)

    # Benchmark comparison (live market data via yfinance)
    try:
        benchmark = compute_benchmark_comparison(schemes)
    except Exception as e:
        logger.warning("Benchmark comparison skipped: %s", e)
        benchmark = {"scheme_vs_benchmark": [], "error": str(e)}

    xray: Dict[str, Any] = {
        "overall_xirr": portfolio.get("overall_xirr"),
        "total_invested": portfolio.get("total_invested", 0),
        "total_current_value": portfolio.get("total_current_value", 0),
        "absolute_gain": portfolio.get("total_current_value", 0) - portfolio.get("total_invested", 0),
        "schemes": schemes,
        "overlap_analysis": overlap,
        "expense_drag": expense,
        "benchmark_comparison": benchmark,
    }

    try:
        rebalancing = generate_rebalancing_plan(xray, user_profile)
        xray["rebalancing_plan"] = rebalancing
    except Exception as e:
        logger.error("Rebalancing generation failed: %s", e)
        xray["rebalancing_plan"] = {"recommendations": "Unable to generate — please retry.", "error": str(e)}

    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "portfolio_xray": xray,
        }
    }
