"""RBI RSS + SEBI listings → PDF text → Chroma embeddings.

Uses **pypdf** (not pdfplumber) so we do not pull a second pdfminer.six pin:
casparser requires pdfminer.six==20240706; pdfplumber wheels pin newer pdfminer and break installs.
"""

from __future__ import annotations

import io
import logging
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup

from app.core.rag import chroma_ids_for_source, embed_and_upsert

logger = logging.getLogger("creda.crawler.reg")

RBI_RSS = "https://www.rbi.org.in/scripts/rss_notification.aspx"
SEBI_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=3"

_pypdf_warned = False


def _extract_pdf_text(pdf_bytes: io.BytesIO) -> str:
    """Extract plain text from a PDF stream; returns empty string if pypdf missing."""
    global _pypdf_warned
    try:
        from pypdf import PdfReader
    except ImportError:
        if not _pypdf_warned:
            _pypdf_warned = True
            logger.warning(
                "pypdf is not installed — RBI/SEBI PDF crawlers are skipped. "
                "Install: pip install -r requirements.txt (see pypdf)."
            )
        return ""
    try:
        reader = PdfReader(pdf_bytes)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        logger.debug("PDF text extract failed: %s", e)
        return ""


def crawl_rbi_circulars(db: Any) -> int:
    """Feedparser → PDF → chunk → Chroma."""
    feed = feedparser.parse(RBI_RSS)
    n = 0
    for entry in getattr(feed, "entries", []) or []:
        circular_id = entry.get("id", entry.get("link", ""))
        if circular_id and chroma_ids_for_source(str(circular_id)):
            continue
        try:
            resp = requests.get(entry.get("link", ""), timeout=60)
            if "pdf" not in resp.headers.get("Content-Type", "").lower() and not resp.content.startswith(b"%PDF"):
                continue
            pdf_bytes = io.BytesIO(resp.content)
            full_text = _extract_pdf_text(pdf_bytes)
            if not full_text.strip():
                continue
            chunks = [c.strip() for c in full_text.split("\n\n") if len(c.strip()) > 100]
            for i, chunk in enumerate(chunks[:80]):
                embed_and_upsert(
                    text=chunk,
                    metadata={
                        "source_id": circular_id,
                        "source": "RBI",
                        "title": entry.get("title", ""),
                        "published": entry.get("published", ""),
                        "last_updated": entry.get("published", ""),
                        "url": entry.get("link", ""),
                        "chunk_index": i,
                        "circular_no": "",
                    },
                )
                n += 1
        except Exception as e:
            logger.debug("RBI entry skip: %s", e)
    return n


def crawl_sebi_circulars(db: Any) -> int:
    """SEBI listing page → PDF links (best-effort)."""
    try:
        resp = requests.get(SEBI_URL, timeout=60)
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.warning("SEBI crawl failed: %s", e)
        return 0
    n = 0
    for row in soup.select("table tr"):
        cols = row.find_all("td")
        if len(cols) < 3:
            continue
        link_tag = cols[1].find("a", href=True)
        if not link_tag:
            continue
        pdf_url = link_tag["href"]
        if not pdf_url.startswith("http"):
            pdf_url = "https://www.sebi.gov.in" + pdf_url
        if chroma_ids_for_source(pdf_url):
            continue
        title = link_tag.get_text(strip=True)
        try:
            r = requests.get(pdf_url, timeout=60)
            pdf_bytes = io.BytesIO(r.content)
            full_text = _extract_pdf_text(pdf_bytes)
            if not full_text.strip():
                continue
            chunks = [c.strip() for c in full_text.split("\n\n") if len(c.strip()) > 100]
            for i, chunk in enumerate(chunks[:50]):
                embed_and_upsert(
                    text=chunk,
                    metadata={
                        "source_id": pdf_url,
                        "source": "SEBI",
                        "title": title,
                        "published": "",
                        "last_updated": "",
                        "url": pdf_url,
                        "chunk_index": i,
                        "circular_no": "",
                    },
                )
                n += 1
        except Exception:
            continue
    return n
