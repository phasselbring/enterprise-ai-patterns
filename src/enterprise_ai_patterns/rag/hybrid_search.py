from dataclasses import dataclass

@dataclass(frozen=True)
class Hit:
    chunk_id: str
    score: float

def reciprocal_rank_fusion(keyword_hits, vector_hits, *, k=60, limit=20):
    scores = {}
    for rank, hit in enumerate(keyword_hits, start=1):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
    for rank, hit in enumerate(vector_hits, start=1):
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
    fused = [Hit(chunk_id=i, score=s) for i, s in scores.items()]
    return sorted(fused, key=lambda h: h.score, reverse=True)[:limit]
