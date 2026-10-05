import sys
import types

from enterprise_ai_patterns.rag.pipeline import Chunk
from enterprise_ai_patterns.rag.reranker import CrossEncoderReranker


class FakeModel:
    def __init__(self, model_name):
        self.model_name = model_name

    def predict(self, pairs):
        return [0.1, 0.9]


def test_cross_encoder_adapter_is_pluggable(monkeypatch):
    fake_module = types.SimpleNamespace(CrossEncoder=FakeModel)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    reranker = CrossEncoderReranker("synthetic-model")
    chunks = [
        Chunk("a", "irrelevant", ("legal",), "x://a"),
        Chunk("b", "termination clause", ("legal",), "x://b"),
    ]
    ranked = reranker.rerank("termination", chunks, limit=2)
    assert ranked[0].chunk_id == "b"
    assert ranked[0].rerank_score == 0.9
