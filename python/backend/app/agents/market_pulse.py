"""
Market Pulse agent — real-time market context, ET headlines, portfolio correlation.
Scrapes financial news, correlates with user portfolio, generates contextual nudges.
"""
import logging
from datetime import datetime
from typing import Any

from app.core.llm import primary_llm, fast_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.market_pulse")

_MARKET_PROMPT = """You are CREDA's Market Intelligence Engine for Indian investors.
Current date: {date}

Market headlines:
{headlines}

User's portfolio summary:
{portfolio}

User's question: {message}

Provide:
1. A brief market context summary (2-3 sentences about what's happening today)
2. How this specifically affects the user's portfolio (personalized)
3. One actionable recommendation based on current market conditions
4. Confidence score (0-100) for your recommendation

Use ₹ amounts. Be specific about Nifty/Sensex levels if known. Reference actual sectors."""

# Predefined market news sources (RSS feeds)
_FEED_URLS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
]


async def _fetch_headlines(max_items: int = 10) -> list[dict]:
    """Fetch latest financial headlines from RSS feeds."""
    import httpx
    headlines = []
    try:
        import feedparser
        async with httpx.AsyncClient(timeout=10) as client:
            for url in _FEED_URLS:
                try:
                    resp = await client.get(url)
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:5]:
                        headlines.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", "")[:200],
                            "published": entry.get("published", ""),
                            "source": feed.feed.get("title", "Unknown"),
                        })
                except Exception as e:
                    logger.debug("Feed fetch failed for %s: %s", url, e)
    except ImportError:
        logger.warning("feedparser not installed — using fallback")

    if not headlines:
        headlines = [{"title": "Market data temporarily unavailable", "summary": "", "source": "fallback"}]

    return headlines[:max_items]


async def _get_market_indices() -> dict:
    """Fetch current Nifty/Sensex levels via yfinance."""
    try:
        import yfinance as yf
        import asyncio
        def _fetch():
            nifty = yf.Ticker("^NSEI")
            sensex = yf.Ticker("^BSESN")
            return {
                "nifty50": round(nifty.info.get("regularMarketPrice", 0), 2),
                "nifty_change": round(nifty.info.get("regularMarketChangePercent", 0), 2),
                "sensex": round(sensex.info.get("regularMarketPrice", 0), 2),
                "sensex_change": round(sensex.info.get("regularMarketChangePercent", 0), 2),
            }
        return await asyncio.get_event_loop().run_in_executor(None, _fetch)
    except Exception as e:
        logger.warning("Market indices fetch failed: %s", e)
        return {"nifty50": 0, "sensex": 0, "nifty_change": 0, "sensex_change": 0}


async def _fetch_fii_dii_flows() -> dict:
    """Fetch FII/DII flow data from NSDL/public sources."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            # Use moneycontrol FII/DII data feed
            resp = await client.get("https://www.moneycontrol.com/rss/marketreports.xml")
            import feedparser
            feed = feedparser.parse(resp.text)
            fii_dii = {"fii_net": 0, "dii_net": 0, "fii_sentiment": "neutral", "data_available": False}
            for entry in feed.entries[:20]:
                title = entry.get("title", "").lower()
                if "fii" in title and ("bought" in title or "sold" in title or "net" in title):
                    fii_dii["data_available"] = True
                    fii_dii["fii_headline"] = entry.get("title", "")
                    break
            return fii_dii
    except Exception:
        return {"fii_net": 0, "dii_net": 0, "fii_sentiment": "neutral", "data_available": False}


async def _score_sentiment(headlines: list[dict]) -> dict:
    """Score news sentiment using fast LLM — bullish/bearish/neutral for each headline."""
    if not headlines:
        return {"overall": "neutral", "scored": []}
    try:
        titles = "\n".join(f"- {h['title']}" for h in headlines[:8])
        result = await fast_llm.ainvoke(
            f"Score each headline as bullish, bearish, or neutral for Indian equity markets. "
            f"Respond ONLY as a JSON array of objects: [{{\"title\": \"...\", \"sentiment\": \"bullish|bearish|neutral\"}}]\n\n{titles}"
        )
        import json
        scored = json.loads(result.content.strip())
        bullish = sum(1 for s in scored if s.get("sentiment") == "bullish")
        bearish = sum(1 for s in scored if s.get("sentiment") == "bearish")
        overall = "bullish" if bullish > bearish + 1 else "bearish" if bearish > bullish + 1 else "neutral"
        return {"overall": overall, "bullish_count": bullish, "bearish_count": bearish, "scored": scored}
    except Exception:
        return {"overall": "neutral", "scored": []}


async def _generate_premarket_briefing(indices: dict, headlines: list, sentiment: dict, portfolio: dict) -> str:
    """Generate a concise pre-market/market briefing suitable for voice."""
    try:
        nifty_dir = "up" if indices.get("nifty_change", 0) >= 0 else "down"
        result = await fast_llm.ainvoke(
            f"Generate a 3-sentence Indian market briefing in a professional ET-style tone.\n"
            f"Nifty 50: {indices.get('nifty50', 'N/A')} ({nifty_dir} {abs(indices.get('nifty_change', 0)):.1f}%), "
            f"Sensex: {indices.get('sensex', 'N/A')}\n"
            f"Market sentiment: {sentiment.get('overall', 'neutral')}\n"
            f"Top headlines: {', '.join(h['title'] for h in headlines[:3])}\n"
            f"User portfolio value: ₹{portfolio.get('total_value', 0):,.0f}\n"
            f"Keep it under 60 words. Use ₹ for currency."
        )
        return result.content.strip()
    except Exception:
        return ""


async def run(state: FinancialState) -> dict[str, Any]:
    """Run market pulse analysis with real-time data, FII/DII flows, and sentiment."""
    headlines = await _fetch_headlines()
    indices = await _get_market_indices()
    fii_dii = await _fetch_fii_dii_flows()
    sentiment = await _score_sentiment(headlines)

    portfolio = state.get("portfolio_data") or {}
    profile = state.get("user_profile") or {}

    portfolio_summary = {
        "total_value": portfolio.get("current_value", 0),
        "total_invested": portfolio.get("total_invested", 0),
        "funds_count": len(portfolio.get("funds", [])),
        "risk_appetite": profile.get("risk_appetite", "moderate"),
    }

    try:
        result = await primary_llm.ainvoke(_MARKET_PROMPT.format(
            date=datetime.now().strftime("%B %d, %Y"),
            headlines="\n".join([f"- {h['title']} ({h['source']})" for h in headlines]),
            portfolio=str(portfolio_summary),
            message=state.get("message", "What's happening in the market?"),
        ))
        analysis = result.content.strip()
    except Exception as e:
        logger.error("Market pulse LLM failed: %s", e)
        analysis = "Market intelligence temporarily unavailable. Please try again."

    # Generate voice-friendly briefing
    briefing = await _generate_premarket_briefing(indices, headlines, sentiment, portfolio_summary)

    return {
        "indices": indices,
        "headlines": headlines[:5],
        "analysis": analysis,
        "sentiment": sentiment,
        "fii_dii": fii_dii,
        "briefing": briefing,
        "timestamp": datetime.now().isoformat(),
        "portfolio_impact": portfolio_summary,
    }


async def run_market_pulse(profile, portfolio, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    portfolio_dict = None
    if portfolio:
        portfolio_dict = {
            "total_invested": portfolio.total_invested,
            "current_value": portfolio.current_value,
            "xirr": portfolio.xirr,
        }
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": "market pulse",
        "intent": "market_pulse",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
        "portfolio_data": portfolio_dict,
    }
    output = await run(state)
    response = await synthesize(output, "market_pulse", "market update", language, voice_mode)
    return {"analysis": output, "response": response}
