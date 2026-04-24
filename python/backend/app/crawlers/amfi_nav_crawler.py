"""Download AMFI NAV ALL file and upsert fund_nav."""

from __future__ import annotations

import logging
from datetime import datetime

import requests
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("creda.crawler.nav")

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


async def fetch_and_upsert_nav(db: AsyncSession) -> int:
    """Parse pipe-delimited NAV file and upsert fund_nav."""
    resp = requests.get(AMFI_NAV_URL, timeout=60)
    resp.raise_for_status()
    lines = [ln for ln in resp.text.splitlines() if ln.strip() and not ln.startswith("Scheme")]
    count = 0
    for line in lines:
        parts = line.split("|")
        if len(parts) < 6:
            continue
        isin = parts[1].strip() or parts[2].strip()
        scheme_name = parts[3].strip()
        nav_raw = parts[4].strip()
        nav_date_raw = parts[5].strip()
        if not isin or not nav_raw:
            continue
        try:
            nav_val = float(nav_raw)
        except ValueError:
            continue
        await db.execute(
            text(
                """
                INSERT INTO fund_nav (isin, scheme_name, nav, nav_date, updated_at)
                VALUES (:isin, :sn, :nav, CAST(:nd AS DATE), NOW())
                ON CONFLICT (isin) DO UPDATE SET
                  scheme_name = EXCLUDED.scheme_name,
                  nav = EXCLUDED.nav,
                  nav_date = EXCLUDED.nav_date,
                  updated_at = NOW()
                """
            ),
            {"isin": isin, "sn": scheme_name, "nav": nav_val, "nd": nav_date_raw},
        )
        count += 1
    await db.commit()
    logger.info("AMFI NAV upserted %d rows", count)
    return count
