"""
Opportunity Radar (PS6) — lightweight signal pack from yfinance + heuristics.
Full nightly crawl can extend `signals` without changing the response contract.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.opportunity_radar")


def _parse_tickers(raw: str | None) -> list[str]:
    if not raw:
        return []
    s = raw.strip()
    if s.startswith("["):
        import json

        try:
            arr = json.loads(s)
            out = []
            for x in arr:
                t = str(x).strip().upper().replace(" ", "")
                if t and not t.endswith(".NS"):
                    t = t + ".NS"
                if t:
                    out.append(t)
            return out
        except Exception:
            pass
    out = []
    for p in s.replace(";", ",").split(","):
        t = p.strip().upper()
        if not t:
            continue
        if not t.endswith(".NS") and "." not in t:
            t = t + ".NS"
        out.append(t)
    return out


async def run(state: FinancialState) -> dict[str, Any]:
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data") or {}
    funds = portfolio.get("funds") or []
    watch = [f.get("fund_name", "")[:40] for f in funds[:5]]

    signals: list[dict[str, Any]] = []

    def _yf_surprise(sym: str) -> dict[str, Any] | None:
        try:
            import yfinance as yf

            t = yf.Ticker(sym)
            qe = getattr(t, "quarterly_earnings", None)
            if qe is None or qe.empty:
                return None
            last = qe.iloc[0]
            rev = float(last.get("Revenue", 0) or 0)
            inc = float(last.get("Earnings", 0) or 0)
            return {
                "type": "earnings_snapshot",
                "ticker": sym,
                "headline": f"{sym} latest quarter revenue ₹{rev/1e7:.2f} Cr (yfinance)",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.debug("yfinance %s: %s", sym, e)
            return None

    wl = _parse_tickers(profile.get("watchlist_stocks"))
    base = ["TCS.NS", "HDFCBANK.NS", "RELIANCE.NS"]
    tickers: list[str] = []
    for t in wl + base:
        if t and t not in tickers:
            tickers.append(t)
    tickers = tickers[:8]

    loop = asyncio.get_event_loop()
    for sym in tickers:
        s = await loop.run_in_executor(None, _yf_surprise, sym)
        if s:
            signals.append(s)

    return {
        "status": "live_partial",
        "data_quality": "estimated",
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "headline": "Opportunity Radar",
        "signal_count": len(signals),
        "watchlist_from_portfolio": watch,
        "watchlist_from_profile": wl,
        "signals": signals[:12],
        "preferences_note": "Configure sectors and watchlist in Settings.",
        "user_city": profile.get("city"),
        "pipeline": "MVP: yfinance quarterly snapshots; extend with NSE bulk deals + SEBI insider feeds.",
    }


async def run_opportunity_radar(profile, portfolio_dict: dict | None, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": getattr(profile, "user_id", "") or "",
        "message": "Opportunity radar scan",
        "intent": "opportunity_radar",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
        "portfolio_data": portfolio_dict or {},
    }
    output = await run(state)
    response = await synthesize(output, "opportunity_radar", "market opportunities", language, voice_mode)
    return {"analysis": output, "response": response}
