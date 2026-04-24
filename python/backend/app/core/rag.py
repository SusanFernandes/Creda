"""Chroma helpers — embed chunks and distance-banded retrieval (Part 10)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger("creda.rag")


def embed_and_upsert(
    text: str,
    metadata: dict[str, Any],
    collection_name: str = "creda_knowledge",
) -> None:
    """Upsert a single chunk into Chroma with metadata (sync)."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection(collection_name)
        doc_id = metadata.get("source_id") or metadata.get("url") or text[:80]
        chunk_idx = metadata.get("chunk_index", 0)
        cid = f"{doc_id}_{chunk_idx}"
        collection.upsert(
            ids=[cid],
            documents=[text],
            metadatas=[metadata],
        )
    except Exception as e:
        logger.warning("embed_and_upsert failed: %s", e)


def chroma_ids_for_source(source_id: str, collection_name: str = "creda_knowledge") -> list[str]:
    """Return chunk ids already stored for a regulatory source_id."""
    try:
        import chromadb
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        collection = client.get_or_create_collection(collection_name)
        res = collection.get(where={"source_id": source_id}, include=[])
        return list(res.get("ids") or [])
    except Exception as e:
        logger.debug("chroma_ids_for_source: %s", e)
        return []


def partition_chroma_results(
    documents: list[str],
    metadatas: list[dict[str, Any]],
    distances: list[float],
) -> tuple[list[str], list[str], list[dict[str, Any]], str | None]:
    """
    Part 10.1: distance < 0.5 → high relevance; < 0.75 → possibly relevant.
    Returns (high_chunks, maybe_chunks, sources_for_ui, latest_published_iso).
    """
    high_chunks: list[str] = []
    maybe_chunks: list[str] = []
    sources: list[dict[str, Any]] = []
    latest_pub: str | None = None

    for doc, meta, dist in zip(documents, metadatas, distances):
        meta = meta or {}
        pub = meta.get("published") or meta.get("last_updated") or ""
        if pub and (latest_pub is None or pub > latest_pub):
            latest_pub = pub

        if dist < 0.5:
            high_chunks.append(doc)
            rel = "high"
        elif dist < 0.75:
            maybe_chunks.append(doc)
            rel = "possible"
        else:
            continue

        sources.append(
            {
                "regulator": meta.get("source", ""),
                "title": meta.get("title", ""),
                "published": pub,
                "url": meta.get("url", ""),
                "relevance": rel,
                "circular_no": meta.get("circular_no", ""),
            }
        )

    return high_chunks, maybe_chunks, sources, latest_pub
