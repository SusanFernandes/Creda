"""Benchmark CAGR via yfinance + RSS headlines for market pulse."""

from __future__ import annotations

import logging
import feedparser
import yfinance as yf
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("creda.crawler.market")

BENCHMARKS = {
    "nifty_50": "^NSEI",
    "nifty_midcap_150": "NIFTY_MIDCAP_150.NS",
    "nifty_smallcap_250": "NIFTY_SMLCAP_250.NS",
}


async def fetch_benchmark_returns(db: AsyncSession) -> int:
    count = 0
    for name, ticker in BENCHMARKS.items():
        try:

            def _dl():
                return yf.download(ticker, period="5y", interval="1d", progress=False)

            data = await __import__("asyncio").to_thread(_dl)
            if data is None or getattr(data, "empty", True):
                continue
            close = data["Close"].dropna()
            if len(close) < 50:
                continue

            def cagr(years: int) -> float | None:
                days = years * 252
                if len(close) < days:
                    return None
                return float((close.iloc[-1] / close.iloc[-days]) ** (1.0 / years) - 1.0)

            c1, c3, c5 = cagr(1), cagr(3), cagr(5)
            await db.execute(
                text(
                    """
                    INSERT INTO benchmark_returns (ticker, name, cagr_1y, cagr_3y, cagr_5y, updated_at)
                    VALUES (:ticker, :name, :c1, :c3, :c5, NOW())
                    ON CONFLICT (ticker) DO UPDATE SET
                      cagr_1y = EXCLUDED.cagr_1y,
                      cagr_3y = EXCLUDED.cagr_3y,
                      cagr_5y = EXCLUDED.cagr_5y,
                      updated_at = NOW()
                    """
                ),
                {"ticker": ticker, "name": name, "c1": c1, "c3": c3, "c5": c5},
            )
            count += 1
        except Exception as e:
            logger.warning("benchmark %s: %s", ticker, e)
    await db.commit()
    return count


def fetch_news_for_market_pulse() -> list[dict[str, str]]:
    feeds = {
        "ET Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "Moneycontrol": "https://www.moneycontrol.com/rss/mfnews.xml",
    }
    headlines: list[dict[str, str]] = []
    for source, url in feeds.items():
        feed = feedparser.parse(url)
        for entry in (getattr(feed, "entries", None) or [])[:15]:
            headlines.append(
                {
                    "headline": entry.get("title", ""),
                    "summary": (entry.get("summary", "") or "")[:300],
                    "published": entry.get("published", ""),
                    "source": source,
                    "url": entry.get("link", ""),
                }
            )
    headlines.sort(key=lambda x: x["published"], reverse=True)
    return headlines[:30]
