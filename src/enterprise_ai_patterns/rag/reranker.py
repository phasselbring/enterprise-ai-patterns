from __future__ import annotations

from dataclasses import replace
from math import log1p
import re
from typing import Iterable, Protocol

from .pipeline import Chunk


_TOKEN = re.compile(r"[A-Za-z0-9_'-]+")


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN.finditer(text)}


class Reranker(Protocol):
    def rerank(self, query: str, chunks: Iterable[Chunk], *, limit: int = 6) -> list[Chunk]: ...


class TokenOverlapReranker:
    """Dependency-free reranker used by tests and demos.

    It deliberately represents a *second-stage* scorer: it sees the query and complete candidate
    text, then computes a new relevance score. Production systems can swap it for a cross-encoder
    or provider reranking API without changing the pipeline.
    """

    def __init__(self, *, retrieval_weight: float = 0.20) -> None:
        if not 0 <= retrieval_weight <= 1:
            raise ValueError("retrieval_weight must be between 0 and 1")
        self._retrieval_weight = retrieval_weight

    def rerank(self, query: str, chunks: Iterable[Chunk], *, limit: int = 6) -> list[Chunk]:
        q = _tokens(query)
        scored: list[Chunk] = []

        for chunk in chunks:
            d = _tokens(chunk.text)
            overlap = len(q & d) / max(1, len(q))
            retrieval_component = log1p(max(0.0, chunk.retrieval_score))
            score = ((1 - self._retrieval_weight) * overlap) + (
                self._retrieval_weight * retrieval_component
            )
            scored.append(replace(chunk, rerank_score=score))

        scored.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return scored[:limit]


class CrossEncoderReranker:
    """Optional production-style cross-encoder adapter.

    Install `.[rerank]`, then pass a model name that your evaluation proves is appropriate for
    the domain. No particular public model is assumed by this reference implementation.
    """

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError('Install the "rerank" extra: pip install -e ".[rerank]"') from exc
        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: Iterable[Chunk], *, limit: int = 6) -> list[Chunk]:
        items = list(chunks)
        if not items:
            return []
        pairs = [(query, chunk.text) for chunk in items]
        scores = self._model.predict(pairs)
        ranked = [replace(chunk, rerank_score=float(score)) for chunk, score in zip(items, scores)]
        ranked.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return ranked[:limit]
