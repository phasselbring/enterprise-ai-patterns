from enterprise_ai_patterns.rag.pipeline import Chunk
from enterprise_ai_patterns.rag.post_retrieval import ContextBuilder


def test_context_builder_deduplicates_chunks():
    chunk = Chunk("c1", "text", ("legal",), "x://1")
    bundle = ContextBuilder(max_chars=100).build([chunk, chunk])
    assert [c.chunk_id for c in bundle.chunks] == ["c1"]
    assert 'source_id="c1"' in bundle.rendered
