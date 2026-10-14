from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Protocol

from .hybrid_search import Hit, reciprocal_rank_fusion
from .pipeline import Caller, Chunk


class RankedIndex(Protocol):
    def search(self, query: str, *, limit: int, allowed_ids: frozenset[str]) -> list[Hit]: ...


class HybridRetriever:
    """First-stage retrieval: lexical + dense search followed by rank fusion."""

    def __init__(
        self,
        *,
        keyword_index: RankedIndex,
        vector_index: RankedIndex,
        chunks: Mapping[str, Chunk],
        fusion_k: int = 60,
    ) -> None:
        self._keyword_index = keyword_index
        self._vector_index = vector_index
        self._chunks = chunks
        self._fusion_k = fusion_k

    def search(self, query: str, *, limit: int = 20, caller: Caller) -> list[Chunk]:
        # Fail closed: compute visibility before ranking/candidate truncation.
        allowed_ids = frozenset(cid for cid, chunk in self._chunks.items()
                                if set(caller.groups).intersection(chunk.allowed_groups))
        if not allowed_ids:
            return []
        # Index adapters MUST implement allowed_ids filtering inside the search backend.
        # Filtering after top-k is insufficient (authorized results could be starved).
        first_stage_limit = max(limit * 2, limit)
        keyword = self._keyword_index.search(query, limit=first_stage_limit, allowed_ids=allowed_ids)
        vector = self._vector_index.search(query, limit=first_stage_limit, allowed_ids=allowed_ids)
        fused = reciprocal_rank_fusion(
            keyword,
            vector,
            k=self._fusion_k,
            limit=limit,
        )

        results: list[Chunk] = []
        for hit in fused:
            chunk = self._chunks.get(hit.chunk_id)
            if chunk is not None and hit.chunk_id in allowed_ids:
                results.append(replace(chunk, retrieval_score=hit.score))
        return results
