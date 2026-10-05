from enterprise_ai_patterns.evaluation.metrics import (
    ndcg_at_k, precision_at_k, recall_at_k, reciprocal_rank
)


def test_retrieval_metrics():
    ranked = ["x", "good", "other"]
    relevant = {"good"}
    assert precision_at_k(ranked, relevant, 2) == 0.5
    assert recall_at_k(ranked, relevant, 2) == 1.0
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert 0 < ndcg_at_k(ranked, {"good": 3.0}, 3) < 1
