"""
ET Research agent — RAG + web search + portfolio-aware context + structured source list.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.et_research")

_RESEARCH_PROMPT = """You are CREDA's Research Intelligence Engine.

User question: {message}

Portfolio-aware context (flag when macro news affects these holdings):
{portfolio_context}

Knowledge base:
{kb_context}

Live web excerpts:
{web_context}

Rules:
1. Answer with clear sections; use ₹ for Indian amounts where relevant.
2. Every factual market claim should map to a source you were given (cite [Source: …]).
3. Note if data may be delayed.
4. End with a short "Portfolio angle" bullet if holdings are known.

Confidence (0-100) on last line as: CONFIDENCE: <n>"""


def _portfolio_context_block(profile: dict, portfolio: dict | None) -> str:
    if not portfolio:
        return "No portfolio loaded — give general education only for portfolio-specific questions."
    funds = portfolio.get("funds") or []
    lines = [
        f"Total portfolio value: ₹{portfolio.get('current_value', 0):,.0f}",
        f"Overall XIRR (portfolio): {portfolio.get('xirr', 0)}%",
    ]
    for f in funds[:12]:
        lines.append(
            f"- {f.get('fund_name', '?')}: category={f.get('category')}, "
            f"value=₹{float(f.get('current_value') or 0):,.0f}, plan={f.get('plan_type')}"
        )
    inc = profile.get("monthly_income")
    lines.append(f"User income ₹{inc}/mo, risk: {profile.get('risk_tolerance') or profile.get('risk_appetite')}")
    return "\n".join(lines)


async def run(state: FinancialState) -> dict[str, Any]:
    message = state.get("message", "")
    profile = state.get("user_profile") or {}
    portfolio = state.get("portfolio_data")

    kb_docs = []
    try:
        import chromadb
        from app.config import settings

        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection("creda_knowledge")
        results = collection.query(query_texts=[message], n_results=5)
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if results.get("distances") else 1.0
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                if distance < 0.7:
                    kb_docs.append({
                        "content": doc,
                        "source": metadata.get("source", "CREDA Knowledge Base"),
                        "category": metadata.get("category", "general"),
                        "relevance": round((1 - distance) * 100, 1),
                        "type": "knowledge_base",
                        "date": metadata.get("date", ""),
                    })
    except Exception as e:
        logger.warning("ChromaDB query failed: %s", e)

    web_docs = []
    web_results = []
    try:
        from app.services.web_search import search_web, scrape_article

        web_results = await search_web(message, max_results=4)
        for wr in web_results[:2]:
            content = await scrape_article(wr["url"], max_chars=2000)
            if content:
                web_docs.append({
                    "content": content,
                    "title": wr["title"],
                    "url": wr["url"],
                    "snippet": wr["snippet"],
                    "type": "web",
                })
    except Exception as e:
        logger.warning("Web search failed: %s", e)

    yf_sources: list[dict[str, Any]] = []
    try:
        import asyncio
        import yfinance as yf
        import re

        tickers = re.findall(r"\b([A-Z]{2,15})\.NS\b", message.upper())
        if not tickers:
            tickers = ["^NSEI"]
        for sym in tickers[:3]:

            def _info(s: str):
                t = yf.Ticker(s)
                inf = t.info or {}
                return {
                    "ticker": s,
                    "name": inf.get("shortName") or s,
                    "pe": inf.get("trailingPE"),
                    "price": inf.get("regularMarketPrice") or inf.get("currentPrice"),
                }

            info = await asyncio.get_event_loop().run_in_executor(None, _info, sym)
            yf_sources.append({
                "name": "yfinance",
                "ticker": sym,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "key_fact": f"Price={info.get('price')}, P/E={info.get('pe')}",
            })
    except Exception as e:
        logger.debug("yfinance enrich skipped: %s", e)

    kb_context = "\n\n".join(
        f"[Source: {d['source']}]\n{d['content']}" for d in kb_docs
    ) if kb_docs else "No knowledge base matches."

    web_context = "\n\n".join(
        f"[Source: {d['title']} | {d['url']}]\n{d['content'][:1500]}"
        for d in web_docs
    ) if web_docs else "No live web results."

    portfolio_context = _portfolio_context_block(profile, portfolio)

    try:
        result = await primary_llm.ainvoke(
            _RESEARCH_PROMPT.format(
                message=message,
                portfolio_context=portfolio_context,
                kb_context=kb_context,
                web_context=web_context,
            )
        )
        analysis = result.content.strip()
    except Exception as e:
        logger.error("ET Research LLM failed: %s", e)
        analysis = "Research analysis temporarily unavailable."

    structured_sources: list[dict[str, Any]] = []
    for d in kb_docs:
        structured_sources.append({
            "name": d["source"],
            "date": d.get("date") or "",
            "key_fact": (d["content"] or "")[:200],
            "type": "knowledge_base",
        })
    for d in web_docs:
        structured_sources.append({
            "name": d["title"],
            "date": "",
            "key_fact": d.get("snippet", "")[:200],
            "url": d.get("url"),
            "type": "web",
        })
    structured_sources.extend(yf_sources)

    avg_kb = sum(d["relevance"] for d in kb_docs) / len(kb_docs) if kb_docs else 0
    web_boost = 15 if web_docs else 0
    confidence = min(round(avg_kb * 1.2 + web_boost + (10 if yf_sources else 0)), 100) if (
        kb_docs or web_docs or yf_sources
    ) else 50

    return {
        "analysis": analysis,
        "sources": structured_sources,
        "portfolio_context_used": bool(portfolio and portfolio.get("funds")),
        "confidence_score": confidence,
        "verified": confidence >= 70,
        "verified_badge": (
            "CREDA Verified — backed by regulatory data and curated research"
            if confidence >= 70
            else "CREDA Analysis — general financial intelligence"
        ),
        "query": message,
        "has_web_results": len(web_results) > 0,
    }


async def run_et_research(message: str, profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    from app.database import AsyncSessionLocal
    from app.models import Portfolio, PortfolioFund
    from sqlalchemy import select

    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    portfolio_dict = None
    if profile:
        async with AsyncSessionLocal() as db:
            port_result = await db.execute(
                select(Portfolio).where(Portfolio.user_id == profile.user_id).order_by(Portfolio.created_at.desc())
            )
            portfolio = port_result.scalar_one_or_none()
            if portfolio:
                funds_result = await db.execute(
                    select(PortfolioFund).where(PortfolioFund.portfolio_id == portfolio.id)
                )
                funds = funds_result.scalars().all()
                portfolio_dict = {
                    "total_invested": portfolio.total_invested,
                    "current_value": portfolio.current_value,
                    "xirr": portfolio.xirr,
                    "funds": [{c.name: getattr(f, c.name) for c in PortfolioFund.__table__.columns} for f in funds],
                }

    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": message,
        "intent": "et_research",
        "language": language,
        "voice_mode": voice_mode,
        "history": [],
        "user_profile": profile_dict,
        "portfolio_data": portfolio_dict,
    }
    output = await run(state)
    response = await synthesize(output, "et_research", message, language, voice_mode)
    return {"analysis": output, "response": response}
