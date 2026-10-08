"""Exact document identity boosts for ranking."""
from __future__ import annotations

import re
from dataclasses import replace

from rag_core.gateway.models import Evidence

_IDENTIFIER = re.compile(r"[\W_]+", re.UNICODE)


def normalize_exact_match(value: str) -> str:
    """Normalize case and identifier separators for exact matching."""
    return _IDENTIFIER.sub("", value).casefold()


def apply_exact_match_boost(
    query: str,
    evidence: Evidence,
    *,
    exact_id_boost: float = 1.0,
    exact_slug_title_boost: float = 0.7,
) -> Evidence:
    """Add a fixed score bonus for an exact ID, slug, or multi-word title."""
    normalized_query = normalize_exact_match(query)
    if not normalized_query:
        return evidence
    identifiers = (evidence.document_id, evidence.canonical_id or "")
    if any(normalized_query == normalize_exact_match(value.split(":", 1)[-1]) for value in identifiers):
        return replace(evidence, retrieval_score=evidence.retrieval_score + exact_id_boost)
    slug = evidence.metadata.get("slug")
    if isinstance(slug, str) and normalized_query == normalize_exact_match(slug):
        return replace(evidence, retrieval_score=evidence.retrieval_score + exact_slug_title_boost)
    if len(query.split()) > 1 and normalized_query == normalize_exact_match(evidence.title):
        return replace(evidence, retrieval_score=evidence.retrieval_score + exact_slug_title_boost)
    return evidence
