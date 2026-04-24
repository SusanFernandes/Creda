"""
Web search service — DuckDuckGo instant answers + page scraping for ET Research.
Free, no API key. Rate-limited with retry logic to avoid being blocked.
"""
import asyncio
import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger("creda.web_search")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Rate limiting: track last request time, min 2s between requests
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 2.0  # seconds between DDG requests
_MAX_RETRIES = 2
_RETRY_DELAY = 3.0  # seconds between retries


async def _rate_limit():
    """Enforce minimum interval between web search requests."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


async def search_web(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """
    Search DuckDuckGo HTML results for a financial query.
    Includes rate limiting and retry logic.
    Returns list of { title, url, snippet }.
    """
    results = []
    search_query = f"{query} site:economictimes.com OR site:moneycontrol.com OR site:livemint.com OR site:valueresearchonline.com"
    params = {"q": search_query, "t": "h_", "ia": "web"}

    for attempt in range(_MAX_RETRIES + 1):
        try:
            await _rate_limit()
            async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get("https://html.duckduckgo.com/html/", params=params)
                if resp.status_code == 429:
                    # Rate limited — wait and retry
                    logger.warning("DuckDuckGo rate limited (429), retrying in %.0fs...", _RETRY_DELAY * (attempt + 1))
                    await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
                if resp.status_code != 200:
                    logger.warning("DuckDuckGo returned %d", resp.status_code)
                    return results

            html = resp.text

            # Parse results from HTML (simple regex extraction)
            # DuckDuckGo HTML results have class="result__a" for links
            link_pattern = re.compile(
                r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
                r'class="result__snippet"[^>]*>(.*?)</(?:a|span|td)',
                re.DOTALL,
            )

            for match in link_pattern.finditer(html):
                raw_url = match.group(1)
                title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
                snippet = re.sub(r"<[^>]+>", "", match.group(3)).strip()

                # DuckDuckGo wraps URLs in a redirect; extract actual URL
                if "uddg=" in raw_url:
                    from urllib.parse import unquote, parse_qs, urlparse
                    parsed = urlparse(raw_url)
                    qs = parse_qs(parsed.query)
                    url = unquote(qs.get("uddg", [raw_url])[0])
                else:
                    url = raw_url

                if title and url.startswith("http"):
                    results.append({"title": title, "url": url, "snippet": snippet})
                    if len(results) >= max_results:
                        break

            # Success — break retry loop
            break

        except httpx.TimeoutException:
            logger.warning("Web search timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES + 1)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY)
                continue
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            break

    return results


async def scrape_article(url: str, max_chars: int = 3000) -> str:
    """
    Scrape main text content from a financial article URL.
    Rate-limited. Returns plain text, truncated to max_chars.
    """
    try:
        await _rate_limit()
        async with httpx.AsyncClient(headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return ""
            html = resp.text

        # Remove script/style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

        # Extract text from <p> tags (most article content)
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
        text = "\n".join(re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:max_chars] if text else ""
    except Exception as e:
        logger.warning("Scrape failed for %s: %s", url, e)
        return ""
