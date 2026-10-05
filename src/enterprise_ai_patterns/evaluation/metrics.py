from __future__ import annotations

from math import log2


def precision_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    top = ranked_ids[:k]
    return len(set(top) & relevant_ids) / k


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    if not relevant_ids:
        return 1.0
    return len(set(ranked_ids[:k]) & relevant_ids) / len(relevant_ids)


def reciprocal_rank(ranked_ids: list[str], relevant_ids: set[str]) -> float:
    for index, item in enumerate(ranked_ids, start=1):
        if item in relevant_ids:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")

    def dcg(values: list[float]) -> float:
        return sum((2**rel - 1) / log2(rank + 1) for rank, rel in enumerate(values, start=1))

    actual = [relevance.get(item, 0.0) for item in ranked_ids[:k]]
    ideal = sorted(relevance.values(), reverse=True)[:k]
    denom = dcg(ideal)
    return 0.0 if denom == 0 else dcg(actual) / denom
