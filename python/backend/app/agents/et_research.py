"""
ET Research agent — financial intelligence combining RAG knowledge base + live web search.
Provides Perplexity-style research with cited sources from real financial websites.
"""
import logging
from typing import Any

from app.core.llm import invoke_llm, primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.et_research")

_RESEARCH_PROMPT = """You are CREDA's Research Intelligence Engine, combining curated knowledge with live web data.

User's question: {message}
User's profile context: {profile}

**Knowledge Base (curated, verified):**
{kb_context}

**Live Web Results (recent, unverified):**
{web_context}

Instructions:
1. Synthesize a comprehensive answer using BOTH knowledge base and web sources
2. Cite specific sources with [Source: name] format
3. Include specific data points, numbers, and ₹ amounts where relevant
4. If web results contradict knowledge base, note the discrepancy
5. Provide a "Confidence Score" (0-100) based on evidence strength
6. For market/price data, note that values may be delayed
7. Structure response with clear sections and bullet points
8. If you found real articles, summarize their key insights

Format as a well-structured research report. Use ₹ amounts for Indian context.
Mark any speculative statements clearly with ⚠️."""


async def run(state: FinancialState) -> dict[str, Any]:
    """Research query with ChromaDB knowledge base + live web search + LLM synthesis."""
    message = state.get("message", "")
    profile = state.get("user_profile") or {}

    # 1. Query ChromaDB for curated knowledge
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
                    })
    except Exception as e:
        logger.warning("ChromaDB query failed: %s", e)

    # 2. Live web search for recent information
    web_docs = []
    web_results = []
    try:
        from app.services.web_search import search_web, scrape_article
        web_results = await search_web(message, max_results=4)

        # Scrape top 2 results for full content
        for i, wr in enumerate(web_results[:2]):
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

    # 3. Build context sections
    kb_context = "\n\n".join([
        f"[Source: {d['source']} | Category: {d['category']} | Relevance: {d['relevance']}%]\n{d['content']}"
        for d in kb_docs
    ]) if kb_docs else "No specific knowledge base matches found."

    web_context = "\n\n".join([
        f"[Source: {d['title']} | URL: {d['url']}]\n{d['content'][:1500]}"
        for d in web_docs
    ]) if web_docs else "No live web results available."

    # 4. LLM synthesis
    try:
        result = await invoke_llm(primary_llm, _RESEARCH_PROMPT.format(
            message=message,
            profile=str({k: profile.get(k) for k in ["age", "risk_appetite", "monthly_income", "city"]}),
            kb_context=kb_context,
            web_context=web_context,
        ))
        analysis = result.content.strip()
    except Exception as e:
        logger.error("ET Research LLM failed: %s", e)
        analysis = "Research analysis temporarily unavailable."

    # 5. Compute confidence
    avg_kb = sum(d["relevance"] for d in kb_docs) / len(kb_docs) if kb_docs else 0
    web_boost = 15 if web_docs else 0
    confidence = min(round(avg_kb * 1.2 + web_boost), 100) if (kb_docs or web_docs) else 50

    # 6. Merge all sources for display
    all_sources = [
        {"title": d["source"], "score": d["relevance"], "type": "knowledge_base"}
        for d in kb_docs
    ] + [
        {"title": wr["title"], "url": wr["url"], "score": 0, "type": "web", "snippet": wr["snippet"]}
        for wr in web_results
    ]

    return {
        "analysis": analysis,
        "sources": all_sources,
        "confidence_score": confidence,
        "verified": confidence >= 70,
        "verified_badge": "CREDA Verified — backed by regulatory data and curated research" if confidence >= 70
                         else "CREDA Analysis — general financial intelligence",
        "query": message,
        "has_web_results": len(web_results) > 0,
    }


async def run_et_research(message: str, profile, language: str, voice_mode: bool) -> dict:
    from app.agents.synthesizer import synthesize
    profile_dict = {c.name: getattr(profile, c.name) for c in type(profile).__table__.columns} if profile else {}
    state: FinancialState = {
        "user_id": profile.user_id if profile else "",
        "message": message,
        "intent": "et_research",
        "language": language, "voice_mode": voice_mode, "history": [],
        "user_profile": profile_dict,
    }
    output = await run(state)
    response = await synthesize(output, "et_research", message, language, voice_mode)
    return {"analysis": output, "response": response}
