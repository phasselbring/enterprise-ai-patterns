from enterprise_ai_patterns.rag.hybrid_search import Hit
from enterprise_ai_patterns.rag.pipeline import Chunk, Caller
from enterprise_ai_patterns.rag.retrieval import HybridRetriever


class Index:
    def __init__(self, hits): self.hits = hits
    def search(self, query, *, limit, allowed_ids): return [h for h in self.hits if h.chunk_id in allowed_ids][:limit]


def test_hybrid_retriever_fuses_keyword_and_vector_rankings():
    chunks = {
        "a": Chunk("a", "alpha", ("legal",), "synthetic://a"),
        "b": Chunk("b", "beta", ("legal",), "synthetic://b"),
        "c": Chunk("c", "gamma", ("legal",), "synthetic://c"),
    }
    retriever = HybridRetriever(
        keyword_index=Index([Hit("a", 1.0), Hit("b", 0.9)]),
        vector_index=Index([Hit("b", 1.0), Hit("c", 0.9)]),
        chunks=chunks,
    )
    results = retriever.search("query", limit=3, caller=Caller("lawyer", ("legal",)))
    assert results[0].chunk_id == "b"
    assert results[0].retrieval_score > 0
