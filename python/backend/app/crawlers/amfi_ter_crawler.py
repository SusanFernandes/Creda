"""Discover AMFI TER CSV/XLSX link and upsert fund_ter."""

from __future__ import annotations

import logging

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("creda.crawler.ter")

AMFI_TER_URL = "https://www.amfiindia.com/research-information/ter-ofmutual-fund-schemes"


async def fetch_ter_data(db: AsyncSession) -> int:
    page = requests.get(AMFI_TER_URL, timeout=60)
    soup = BeautifulSoup(page.text, "html.parser")
    link = soup.find("a", href=lambda h: h and (".csv" in h.lower() or ".xlsx" in h.lower()))
    if not link:
        raise ValueError("TER download link not found — AMFI page structure changed")
    href = link.get("href", "")
    ter_url = href if href.startswith("http") else "https://www.amfiindia.com" + href
    count = 0
    if ter_url.endswith(".csv"):
        df = pd.read_csv(ter_url)
    else:
        df = pd.read_excel(ter_url)

    cols = {c.lower(): c for c in df.columns}
    isin_col = cols.get("isin") or cols.get("isin div payout/reinvestment") or list(df.columns)[0]
    name_col = cols.get("scheme name") or cols.get("scheme") or list(df.columns)[1]
    ter_col = cols.get("ter") or cols.get("expense ratio") or cols.get("ratio")

    for _, row in df.iterrows():
        raw_isin = str(row.get(isin_col, "")).strip()
        if not raw_isin or raw_isin.lower() == "nan":
            continue
        name = str(row.get(name_col, "")).strip()
        ter_raw = row.get(ter_col, 0) if ter_col else 0
        try:
            ter_pct = float(ter_raw)
        except (TypeError, ValueError):
            continue
        ter_dec = ter_pct / 100.0 if ter_pct > 0.5 else ter_pct
        plan = "direct" if "direct" in name.lower() else "regular"
        await db.execute(
            text(
                """
                INSERT INTO fund_ter (isin, scheme_name, ter, plan_type, updated_at)
                VALUES (:isin, :sn, :ter, :pt, NOW())
                ON CONFLICT (isin) DO UPDATE SET ter = EXCLUDED.ter, scheme_name = EXCLUDED.scheme_name,
                  updated_at = NOW()
                """
            ),
            {"isin": raw_isin, "sn": name, "ter": ter_dec, "pt": plan},
        )
        count += 1
    await db.commit()
    logger.info("AMFI TER upserted %d rows", count)
    return count
