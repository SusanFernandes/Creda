"""
RAG agent — knowledge base retrieval from ChromaDB (60+ curated financial documents).
"""
import logging
from typing import Any

from app.core.llm import primary_llm
from app.config import settings
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.rag")

_RAG_PROMPT = """You are CREDA, an AI financial coach with access to Indian financial regulations and government scheme documents.
Use ONLY the retrieved context below to answer the user's question. If the context doesn't contain enough information, say so.

Retrieved context:
{context}

User question: {question}

Rules:
- Cite specific regulations or scheme names
- Use ₹ for currency
- Mention eligibility criteria if relevant
- Be factual — don't speculate beyond what's in the context"""


async def run(state: FinancialState) -> dict[str, Any]:
    message = state.get("message", "")

    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_collection("creda_knowledge")

        results = collection.query(
            query_texts=[message],
            n_results=5,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        # Filter by relevance (distance < 0.5)
        relevant = []
        sources = []
        for doc, meta, dist in zip(documents, metadatas, distances):
            if dist < 0.5:
                relevant.append(doc)
                sources.append(meta.get("source", "unknown"))

        if not relevant:
            return {
                "answer": "I don't have specific information about that in my knowledge base. Could you rephrase or ask about a specific government scheme or regulation?",
                "sources": [],
                "confidence": "low",
            }

        context = "\n\n---\n\n".join(relevant)

        result = await primary_llm.ainvoke(_RAG_PROMPT.format(context=context, question=message))

        return {
            "answer": result.content.strip(),
            "sources": list(set(sources)),
            "confidence": "high" if distances[0] < 0.3 else "medium",
        }

    except Exception as e:
        logger.error("RAG query failed: %s", e, exc_info=True)
        return {
            "answer": "I'm having trouble accessing the knowledge base right now. Please try again.",
            "sources": [],
            "confidence": "error",
            "error": str(e),
        }


async def load_knowledge_base(chroma_client):
    """Load knowledge/documents.yaml into ChromaDB. Called on startup."""
    import yaml
    from pathlib import Path

    docs_path = Path(__file__).parent.parent.parent / "knowledge" / "documents.yaml"
    if not docs_path.exists():
        logger.warning("Knowledge base file not found: %s", docs_path)
        return

    with open(docs_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "documents" not in data:
        logger.warning("No documents found in knowledge base YAML")
        return

    collection = chroma_client.get_or_create_collection("creda_knowledge")

    ids = []
    documents = []
    metadatas = []

    for i, doc in enumerate(data["documents"]):
        doc_id = doc.get("id", f"doc_{i}")
        ids.append(doc_id)
        documents.append(doc.get("content", ""))
        metadatas.append({
            "source": doc.get("source", ""),
            "category": doc.get("category", ""),
            "title": doc.get("title", ""),
        })

    if documents:
        # Batch upsert (ChromaDB handles embedding via default model)
        batch_size = 50
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            collection.upsert(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info("Loaded %d documents into ChromaDB", len(documents))
