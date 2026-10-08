"""Embedding-based reranking for gateway evidence."""
from __future__ import annotations

import asyncio
import logging
import math
from collections.abc import Sequence
from dataclasses import replace

import httpx

from rag_core.gateway.models import Evidence

logger = logging.getLogger(__name__)


class RerankAdapter:
    def __init__(self, embedding_provider: object) -> None:
        self._embedding_provider = embedding_provider

    async def rerank(
        self, query: str, documents: Sequence[Evidence], top_k: int
    ) -> list[Evidence]:
        if not documents:
            return []
        try:
            query_embedding = await self._embedding_provider.embed_query(query)
            if query_embedding is None:
                logger.warning("embedding provider returned None; returning retrieval order")
                return list(documents)[:top_k]
            scored: list[Evidence] = []
            for document in documents:
                document_embedding = await self._embedding_provider.embed_query(document.text)
                if document_embedding is None:
                    continue
                score = self._cosine(query_embedding, document_embedding)
                scored.append(replace(document, reranker_score=score))
            if not scored:
                return list(documents)[:top_k]
        except (httpx.HTTPError, OSError, asyncio.TimeoutError) as error:
            logger.warning("embedding reranker unavailable; returning retrieval order: %s", error)
            return list(documents)[:top_k]
        scored.sort(key=lambda document: document.reranker_score or 0.0, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
        if len(left) != len(right):
            raise ValueError("cannot compute cosine for embeddings with different dimensions")
        magnitude = math.sqrt(sum(value * value for value in left)) * math.sqrt(
            sum(value * value for value in right)
        )
        if magnitude == 0:
            return 0.0
        return sum(a * b for a, b in zip(left, right)) / magnitude
