"""APScheduler wiring for CREDA crawlers.

Each crawler module is imported inside a try/except so a missing optional
dependency (e.g. pypdf, pandas, yfinance) cannot abort application startup.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import AsyncSessionLocal

logger = logging.getLogger("creda.scheduler")


def register_data_jobs(scheduler: AsyncIOScheduler) -> None:
    """Register cron jobs; skip any crawler whose dependencies fail to import."""

    # --- AMFI NAV ---
    try:
        from app.crawlers.amfi_nav_crawler import fetch_and_upsert_nav
    except ImportError as e:
        logger.warning("AMFI NAV crawler disabled (import error): %s", e)
    else:

        async def job_nav():
            async with AsyncSessionLocal() as db:
                await fetch_and_upsert_nav(db)

        scheduler.add_job(job_nav, "cron", hour=21, minute=0, id="amfi_nav")

    # --- AMFI TER ---
    try:
        from app.crawlers.amfi_ter_crawler import fetch_ter_data
    except ImportError as e:
        logger.warning("AMFI TER crawler disabled (import error): %s", e)
    else:

        async def job_ter():
            async with AsyncSessionLocal() as db:
                await fetch_ter_data(db)

        scheduler.add_job(job_ter, "cron", day_of_week="sun", hour=22, minute=0, id="amfi_ter")

    # --- Benchmarks ---
    try:
        from app.crawlers.market_data_crawler import fetch_benchmark_returns
    except ImportError as e:
        logger.warning("Benchmark crawler disabled (import error): %s", e)
    else:

        async def job_bench():
            async with AsyncSessionLocal() as db:
                await fetch_benchmark_returns(db)

        scheduler.add_job(job_bench, "cron", hour=18, minute=30, id="benchmarks")

    # --- Regulatory PDF → Chroma (pypdf; import still wrapped) ---
    try:
        from app.crawlers.regulatory_crawler import crawl_rbi_circulars, crawl_sebi_circulars
    except ImportError as e:
        logger.warning("Regulatory crawler module disabled (import error): %s", e)
    else:

        def job_rbi():
            crawl_rbi_circulars(None)

        def job_sebi():
            crawl_sebi_circulars(None)

        scheduler.add_job(job_rbi, "cron", day_of_week="sun", hour=23, minute=0, id="rbi_rss")
        scheduler.add_job(job_sebi, "cron", day_of_week="sun", hour=23, minute=30, id="sebi_html")

    logger.info("Crawler cron jobs registered (some may be skipped if optional deps are missing).")
