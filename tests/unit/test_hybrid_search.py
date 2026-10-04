from enterprise_ai_patterns.rag.hybrid_search import Hit, reciprocal_rank_fusion

def test_rrf_rewards_overlap():
    keyword = [Hit("a", 1.0), Hit("b", 0.8)]
    vector = [Hit("b", 0.95), Hit("c", 0.7)]
    fused = reciprocal_rank_fusion(keyword, vector)
    assert fused[0].chunk_id == "b"
