"""
RAG agent — ChromaDB retrieval with distance bands and source metadata in the answer.
"""
import logging
import re
from datetime import date
from typing import Any

from app.core.llm import primary_llm
from app.core.rag import partition_chroma_results
from app.config import settings
from app.agents.state import FinancialState

logger = logging.getLogger("creda.agents.rag")

_RAG_PROMPT = """You are CREDA, an AI financial coach with access to Indian financial regulations and government scheme documents.
Use the retrieved context below where helpful; label uncertain claims clearly.

Highly relevant context:
{high_ctx}

Possibly relevant context (verify before relying on):
{maybe_ctx}

User question: {question}

Rules:
- Cite regulations or schemes when grounded in context
- Use ₹ for currency
- Be factual"""


async def run(state: FinancialState) -> dict[str, Any]:
    message = state.get("message", "")

    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_collection("creda_knowledge")

        results = collection.query(query_texts=[message], n_results=8)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        high_chunks, maybe_chunks, sources, latest_pub = partition_chroma_results(
            documents, metadatas, distances
        )

        if not high_chunks and not maybe_chunks:
            return {
                "answer": (
                    "I don't have specific circular context for that in my knowledge base. "
                    "I can still share general guidance — try naming a scheme (NPS, PPF, ELSS) or regulator."
                ),
                "sources": [],
                "knowledge_cutoff_note": "No qualifying knowledge-base matches (distance ≥ 0.75).",
                "status": "success",
                "data_quality": "partial",
            }

        high_ctx = "\n\n---\n\n".join(high_chunks) if high_chunks else "(none)"
        maybe_ctx = "\n\n---\n\n".join(maybe_chunks) if maybe_chunks else "(none)"

        result = await primary_llm.ainvoke(
            _RAG_PROMPT.format(high_ctx=high_ctx, maybe_ctx=maybe_ctx, question=message)
        )

        cutoff = (
            f"Based on circulars indexed in CREDA through {latest_pub}"
            if latest_pub
            else "Based on indexed regulatory snippets in CREDA"
        )

        return {
            "answer": result.content.strip(),
            "sources": sources[:12],
            "knowledge_cutoff_note": cutoff,
            "status": "success",
            "data_quality": "live",
        }

    except Exception as e:
        logger.error("RAG query failed: %s", e, exc_info=True)
        return {
            "answer": "I'm having trouble accessing the knowledge base right now. Please try again.",
            "sources": [],
            "knowledge_cutoff_note": "",
            "status": "error",
            "data_quality": "partial",
            "error": str(e),
        }


async def load_knowledge_base(chroma_client):
    """Load knowledge/documents.yaml into ChromaDB with required metadata fields."""
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

    today = date.today().isoformat()
    for i, doc in enumerate(data["documents"]):
        doc_id = doc.get("id", f"doc_{i}")
        ids.append(doc_id)
        documents.append(doc.get("content", ""))
        metadatas.append(
            {
                "source": doc.get("source", "IRDAI"),
                "circular_no": doc.get("circular_no", ""),
                "published": doc.get("published", today),
                "last_updated": doc.get("last_updated", today),
                "url": doc.get("url", ""),
                "title": doc.get("title", ""),
                "category": doc.get("category", ""),
            }
        )

    if documents:
        batch_size = 50
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            collection.upsert(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info("Loaded %d documents into ChromaDB", len(documents))
