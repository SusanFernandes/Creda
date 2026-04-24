"""
AMFI NAV Service — fetches real daily NAV data from the official
Association of Mutual Funds in India (amfiindia.com) NAV text file.

Source: https://www.amfiindia.com/spages/NAVAll.txt
Updated daily (except holidays) by AMFI.

This service:
  1. Downloads and parses the full NAV file (~5000+ schemes)
  2. Builds an in-memory lookup by AMFI scheme code and scheme name
  3. Provides fuzzy matching for fund names from CAMS statements
  4. Caches results in Redis for 4 hours to avoid hitting AMFI on every request

Usage:
    nav = await get_fund_nav("Axis Bluechip Fund - Direct Plan - Growth")
    # returns {"nav": 52.34, "date": "24-Apr-2026", "scheme_code": "120503", ...}
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger("creda.amfi_nav")

# ── Constants ──────────────────────────────────────────────────────
AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
_CACHE_TTL = 4 * 3600  # 4 hours
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_HEADERS = {
    "User-Agent": "CREDA-Financial-Coach/2.0 (amfi-nav-fetch)",
    "Accept": "text/plain",
}

# In-memory cache
_nav_cache: dict[str, dict] = {}  # scheme_code -> {nav, date, scheme_name, ...}
_name_index: dict[str, str] = {}  # normalized_name -> scheme_code
_last_fetch: Optional[datetime] = None


def _normalize_name(name: str) -> str:
    """Normalize a fund name for fuzzy matching."""
    name = name.lower().strip()
    # Remove common suffixes and noise
    for noise in [
        "- growth", "growth", "- dividend", "dividend",
        "- direct plan", "direct plan", "- regular plan", "regular plan",
        "- direct", "direct", "- regular", "regular",
        "(formerly", "fund", "scheme", "the", "  ",
    ]:
        name = name.replace(noise, " ")
    name = re.sub(r"[^a-z0-9\s]", "", name)
    return " ".join(name.split())


async def _fetch_and_parse_amfi() -> bool:
    """
    Download NAVAll.txt from AMFI and parse into memory cache.
    Returns True if successful, False otherwise.

    File format (pipe-delimited, grouped by AMC):
    ---
    Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;
    Net Asset Value;Date
    ---
    """
    global _nav_cache, _name_index, _last_fetch

    try:
        async with httpx.AsyncClient(
            headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True
        ) as client:
            resp = await client.get(AMFI_NAV_URL)
            if resp.status_code != 200:
                logger.warning("AMFI NAV fetch failed: HTTP %d", resp.status_code)
                return False

        text = resp.text
        lines = text.strip().split("\n")

        new_cache: dict[str, dict] = {}
        new_index: dict[str, str] = {}
        current_amc = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # AMC header lines don't have semicolons
            if ";" not in line:
                # Could be AMC name or category header
                if "Mutual Fund" in line or "mutual fund" in line.lower():
                    current_amc = line.strip()
                continue

            parts = line.split(";")
            if len(parts) < 6:
                continue

            scheme_code = parts[0].strip()
            if not scheme_code.isdigit():
                continue  # Skip header rows

            isin_growth = parts[1].strip()
            isin_reinv = parts[2].strip()
            scheme_name = parts[3].strip()
            nav_str = parts[4].strip()
            nav_date = parts[5].strip()

            # Parse NAV value
            try:
                nav_value = float(nav_str)
            except (ValueError, TypeError):
                continue  # N.A. or invalid

            entry = {
                "scheme_code": scheme_code,
                "isin_growth": isin_growth,
                "isin_reinvestment": isin_reinv,
                "scheme_name": scheme_name,
                "nav": nav_value,
                "date": nav_date,
                "amc": current_amc,
            }

            new_cache[scheme_code] = entry
            # Build name index for fuzzy matching
            normalized = _normalize_name(scheme_name)
            new_index[normalized] = scheme_code

        if new_cache:
            _nav_cache = new_cache
            _name_index = new_index
            _last_fetch = datetime.utcnow()
            logger.info(
                "AMFI NAV: loaded %d schemes from %d AMCs",
                len(new_cache),
                len(set(e["amc"] for e in new_cache.values() if e["amc"])),
            )
            return True
        else:
            logger.warning("AMFI NAV: parsed 0 schemes — file format may have changed")
            return False

    except Exception as e:
        logger.error("AMFI NAV fetch/parse error: %s", e)
        return False


async def _ensure_cache():
    """Refresh cache if stale or empty."""
    global _last_fetch
    if _nav_cache and _last_fetch and (datetime.utcnow() - _last_fetch) < timedelta(seconds=_CACHE_TTL):
        return  # Cache is fresh
    await _fetch_and_parse_amfi()


async def get_fund_nav(fund_name: str, scheme_code: str = "") -> Optional[dict]:
    """
    Look up the latest NAV for a mutual fund.

    Args:
        fund_name: The fund name (from CAMS statement or user input)
        scheme_code: Optional AMFI scheme code for exact match

    Returns:
        dict with {nav, date, scheme_name, scheme_code, amc, isin_growth} or None
    """
    await _ensure_cache()

    if not _nav_cache:
        return None

    # 1. Try exact scheme code match
    if scheme_code and scheme_code in _nav_cache:
        return _nav_cache[scheme_code]

    # 2. Try exact normalized name match
    normalized = _normalize_name(fund_name)
    if normalized in _name_index:
        code = _name_index[normalized]
        return _nav_cache.get(code)

    # 3. Fuzzy matching — find best substring match
    best_match = None
    best_score = 0
    query_words = set(normalized.split())

    if not query_words:
        return None

    for cached_name, code in _name_index.items():
        cached_words = set(cached_name.split())
        # Jaccard similarity
        intersect = len(query_words & cached_words)
        union = len(query_words | cached_words)
        if union == 0:
            continue
        score = intersect / union

        # Bonus for substring containment
        if normalized in cached_name or cached_name in normalized:
            score += 0.3

        if score > best_score and score > 0.4:
            best_score = score
            best_match = code

    if best_match:
        return _nav_cache[best_match]

    return None


async def get_all_navs_for_portfolio(
    funds: list[dict],
) -> dict[str, dict]:
    """
    Batch lookup NAVs for a portfolio's funds.

    Args:
        funds: list of dicts with at least 'fund_name' key, optionally 'scheme_code'

    Returns:
        dict mapping fund_name -> NAV data dict
    """
    await _ensure_cache()
    results = {}

    for fund in funds:
        name = fund.get("fund_name", "")
        code = fund.get("scheme_code", "")
        nav_data = await get_fund_nav(name, code)
        if nav_data:
            results[name] = nav_data

    return results


async def search_schemes(query: str, max_results: int = 10) -> list[dict]:
    """
    Search AMFI schemes by name. Useful for autocomplete or lookup.

    Args:
        query: Search string
        max_results: Max results to return

    Returns:
        List of matching scheme dicts
    """
    await _ensure_cache()

    if not query or not _nav_cache:
        return []

    query_lower = query.lower()
    results = []

    for entry in _nav_cache.values():
        if query_lower in entry["scheme_name"].lower():
            results.append(entry)
            if len(results) >= max_results:
                break

    return results


def get_cache_stats() -> dict:
    """Return cache status for health checks."""
    return {
        "total_schemes": len(_nav_cache),
        "last_fetch": _last_fetch.isoformat() if _last_fetch else None,
        "cache_age_minutes": round(
            (datetime.utcnow() - _last_fetch).total_seconds() / 60, 1
        )
        if _last_fetch
        else None,
    }
