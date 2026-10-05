from enterprise_ai_patterns.rag.pipeline import Chunk
from enterprise_ai_patterns.rag.reranker import TokenOverlapReranker


def test_reranker_moves_more_relevant_candidate_to_top():
    chunks = [
        Chunk("a", "insurance payment schedule", ("legal",), "x://a", retrieval_score=0.9),
        Chunk("b", "termination for convenience requires written notice", ("legal",), "x://b", retrieval_score=0.4),
    ]
    ranked = TokenOverlapReranker(retrieval_weight=0.05).rerank(
        "termination written notice", chunks, limit=2
    )
    assert ranked[0].chunk_id == "b"
    assert ranked[0].rerank_score is not None
