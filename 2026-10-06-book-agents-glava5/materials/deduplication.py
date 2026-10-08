"""Canonical-document deduplication for retrieved evidence."""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from rag_core.gateway.models import Evidence, EvidenceOrigin

_ORIGIN_PREFERENCE = {
    EvidenceOrigin.LIVE_CORPORATE: 4,
    EvidenceOrigin.LOCAL_SNAPSHOT: 3,
    EvidenceOrigin.AGENT_MEMORY: 2,
    EvidenceOrigin.PUBLIC_WEB: 1,
}


def deduplicate_evidence(evidence: Iterable[Evidence]) -> list[Evidence]:
    """Keep one preferred result per canonical document and retain alternates."""
    groups: dict[str, list[Evidence]] = {}
    order: list[str] = []
    for item in evidence:
        canonical_id = item.canonical_id or item.document_id
        if canonical_id not in groups:
            groups[canonical_id] = []
            order.append(canonical_id)
        groups[canonical_id].append(item)

    deduplicated: list[Evidence] = []
    for canonical_id in order:
        candidates = groups[canonical_id]
        winner = max(
            candidates,
            key=lambda item: (_ORIGIN_PREFERENCE.get(item.origin, 0), item.final_score, item.retrieval_score),
        )
        alternates = [item for item in candidates if item is not winner]
        if alternates:
            metadata = dict(winner.metadata)
            metadata["alternate_sources"] = tuple(item.source for item in alternates)
            metadata["alternate_metadata"] = tuple(dict(item.metadata) for item in alternates)
            winner = replace(winner, metadata=metadata)
        deduplicated.append(winner)
    return deduplicated
