"""
Chart Pattern Intelligence (PS6) — RSI + 52-week proximity via yfinance for a ticker from the message or Nifty.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from app.agents.state import FinancialState


def _resolve_symbol(state: FinancialState) -> str:
    raw = (state.get("chart_symbol") or "").strip().upper()
    if raw:
        if raw.endswith(".NS") or raw.startswith("^"):
            return raw
        return raw + ".NS"
    msg = (state.get("message") or "").upper()
    m = re.search(r"\b([A-Z]{2,15})\.NS\b", msg)
    if m:
        return m.group(1) + ".NS"
    m2 = re.search(r"\b([A-Z]{2,15})\b", msg)
    if m2 and m2.group(1) not in ("THE", "AND", "FOR", "NSE", "BSE"):
        return m2.group(1) + ".NS"
    return "^NSEI"


async def run(state: FinancialState) -> dict[str, Any]:
    sym = _resolve_symbol(state)
    tf = (state.get("chart_timeframe") or "3mo").strip().lower()
    period_map = {"1w": "5d", "1m": "1mo", "3m": "3mo", "1y": "1y"}
    period = period_map.get(tf, "3mo")
    min_bars = 5 if period == "5d" else 30

    def _scan() -> dict[str, Any]:
        import numpy as np
        import yfinance as yf

        t = yf.Ticker(sym)
        h = t.history(period=period)
        if h is None or len(h) < min_bars:
            return {"ticker": sym, "patterns": [], "error": "insufficient_history", "period": period}
        close = h["Close"].astype(float)
        high52 = close.max()
        last = float(close.iloc[-1])
        delta = (last / high52 - 1) * 100
        rsi_period = 14
        delta_s = close.diff()
        gain = (delta_s.where(delta_s > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta_s.where(delta_s < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss.replace(0, 1e-9)
        rsi = 100 - (100 / (1 + rs))
        last_rsi = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
        patterns = []
        if delta > -2:
            patterns.append({
                "name": "52_week_proximity",
                "plain_english": "Price within ~2% of 52-week high — often watched for breakout follow-through.",
                "confidence": "medium",
            })
        if last_rsi > 70:
            patterns.append({
                "name": "rsi_overbought",
                "plain_english": f"RSI({rsi_period}) is {last_rsi:.1f} — momentum stretched; watch for pullback.",
                "confidence": "low",
            })
        elif last_rsi < 35:
            patterns.append({
                "name": "rsi_oversold",
                "plain_english": f"RSI({rsi_period}) is {last_rsi:.1f} — washed-out conditions for swing traders.",
                "confidence": "low",
            })
        return {
            "ticker": sym,
            "last_close": round(last, 2),
            "rsi_14": round(last_rsi, 1),
            "distance_from_52w_high_pct": round(delta, 2),
            "patterns": patterns,
            "period": period,
        }

    scan = await asyncio.get_event_loop().run_in_executor(None, _scan)
    scan["scanned_at"] = datetime.now(timezone.utc).isoformat()
    scan["timeframe"] = tf
    scan["data_quality"] = "live" if not scan.get("error") else "estimated"
    return scan


async def run_chart_pattern(
    profile,
    symbol: str | None,
    timeframe: str,
    language: str,
    voice_mode: bool,
) -> dict:
    from app.agents.synthesizer import synthesize

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": getattr(profile, "user_id", "") or "",
        "message": f"Technical pattern {symbol or 'Nifty'}",
        "intent": "chart_pattern",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
        "chart_symbol": (symbol or "").strip(),
        "chart_timeframe": (timeframe or "3mo").strip(),
    }
    output = await run(state)
    response = await synthesize(output, "chart_pattern", state["message"], language, voice_mode)
    return {"analysis": output, "response": response}
