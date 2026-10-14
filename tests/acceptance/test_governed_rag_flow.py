from enterprise_ai_patterns.rag.pipeline import Caller, Chunk, answer_question

class Retriever:
    def search(self, query, *, limit=20, caller):
        return [c for c in [
            Chunk("allowed", "Florida customer count is 2.", ("sales",), "synthetic://allowed"),
            Chunk("forbidden", "Restricted finance data.", ("finance",), "synthetic://forbidden"),
        ] if set(caller.groups).intersection(c.allowed_groups)]

class Reranker:
    def rerank(self, query, chunks, *, limit=6):
        return list(chunks)[:limit]

class Generator:
    def answer(self, query, context):
        assert [c.chunk_id for c in context] == ["allowed"]
        return "There are 2 Florida customers.", ["allowed"]

class Trace:
    def __init__(self): self.events = []
    def record(self, event): self.events.append(event)

def test_unauthorized_context_never_reaches_generator():
    trace = Trace()
    answer = answer_question(
        caller=Caller("u1", ("sales",)),
        query="How many Florida customers?",
        retriever=Retriever(),
        reranker=Reranker(),
        generator=Generator(),
        trace_sink=trace,
    )
    assert answer.citations == ("synthetic://allowed",)
    assert trace.events[0]["authorized_count"] == 1
