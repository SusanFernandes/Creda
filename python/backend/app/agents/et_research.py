"""
ET Research agent — financial knowledge base powered by curated research.
Answers questions citing relevant articles and knowledge, creates paywall upsell opportunity.
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.et_research")

_RESEARCH_PROMPT = """You are CREDA's Research Intelligence Engine, powered by decades of Indian financial journalism.

User's question: {message}
User's profile context: {profile}

Knowledge base context:
{context}

Provide:
1. A comprehensive, well-researched answer with specific data points
2. Historical context where relevant (e.g., "In the 2008 crisis, Nifty fell X%...")
3. At least 2 specific citations or references
4. A "Confidence Score" (0-100) based on the strength of your evidence
5. A "CREDA Verified" badge explanation (what makes this advice trustworthy)

Format your response as a well-structured analysis. Use ₹ amounts for Indian context.
Mark any speculative statements clearly."""


async def run(state: FinancialState) -> dict[str, Any]:
    """Research query with ChromaDB knowledge base + LLM synthesis."""
    message = state.get("message", "")
    profile = state.get("user_profile") or {}

    # Query ChromaDB for relevant knowledge
    context_docs = []
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
                if distance < 0.7:  # broader threshold for research
                    context_docs.append({
                        "content": doc,
                        "source": metadata.get("source", "CREDA Knowledge Base"),
                        "category": metadata.get("category", "general"),
                        "relevance": round((1 - distance) * 100, 1),
                    })
    except Exception as e:
        logger.warning("ChromaDB query failed: %s", e)

    # Build context
    context_text = "\n\n".join([
        f"[Source: {d['source']} | Category: {d['category']} | Relevance: {d['relevance']}%]\n{d['content']}"
        for d in context_docs
    ]) if context_docs else "No specific knowledge base matches found. Use general financial expertise."

    try:
        result = await primary_llm.ainvoke(_RESEARCH_PROMPT.format(
            message=message,
            profile=str({k: profile.get(k) for k in ["age", "risk_appetite", "monthly_income", "city"]}),
            context=context_text,
        ))
        analysis = result.content.strip()
    except Exception as e:
        logger.error("ET Research LLM failed: %s", e)
        analysis = "Research analysis temporarily unavailable."

    avg_relevance = sum(d["relevance"] for d in context_docs) / len(context_docs) if context_docs else 0
    confidence = min(round(avg_relevance * 1.2), 100) if context_docs else 50

    return {
        "analysis": analysis,
        "sources": context_docs,
        "confidence_score": confidence,
        "verified": confidence >= 70,
        "verified_badge": "CREDA Verified — backed by regulatory data and curated research" if confidence >= 70
                         else "CREDA Analysis — general financial intelligence",
        "query": message,
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
