from enterprise_ai_patterns.rag.pipeline import Chunk
from enterprise_ai_patterns.rag.post_retrieval import ContextBuilder


def chunk(chunk_id, text):
    return Chunk(chunk_id, text, ("g",), f"x://{chunk_id}")


def test_oversized_chunk_is_skipped_not_fatal():
    bundle = ContextBuilder(max_chars=100).build([chunk("big", "x" * 500), chunk("small", "fits")])
    assert [c.chunk_id for c in bundle.chunks] == ["small"]


def test_budget_counts_separators():
    # Two 50-char blocks plus the "\n\n" separator exceed a 100-char budget.
    a, b = chunk("a", "a" * 46), chunk("b", "b" * 46)  # "[a] " + 46 = 50 chars each
    bundle = ContextBuilder(max_chars=100).build([a, b])
    assert len(bundle.rendered) <= 100
    assert len(bundle.chunks) <= 1
