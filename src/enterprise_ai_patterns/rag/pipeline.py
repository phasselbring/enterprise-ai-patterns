from dataclasses import dataclass, field
import uuid


@dataclass(frozen=True)
class Caller:
    user_id: str
    groups: tuple[str, ...]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    allowed_groups: tuple[str, ...]
    source_uri: str
    retrieval_score: float = 0.0
    rerank_score: float | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Answer:
    text: str
    citations: tuple[str, ...]
    trace_id: str


def answer_question(*, caller, query, retriever, reranker, generator, trace_sink):
    """Compact reference flow retained for interview-sized examples."""
    trace_id = str(uuid.uuid4())
    candidates = retriever.search(query, limit=20, caller=caller)
    permitted = [
        c for c in candidates
        if set(caller.groups).intersection(c.allowed_groups)
    ]
    selected = reranker.rerank(query, permitted, limit=6)
    text, cited_ids = generator.answer(query, selected)

    valid = {c.chunk_id for c in selected}
    if any(c not in valid for c in cited_ids):
        raise ValueError("Generator cited unavailable context")

    source_map = {c.chunk_id: c.source_uri for c in selected}
    citations = tuple(source_map[c] for c in cited_ids)
    trace_sink.record({
        "trace_id": trace_id,
        "candidate_count": len(candidates),
        "authorized_count": len(permitted),
        "selected_count": len(selected),
    })
    return Answer(text=text, citations=citations, trace_id=trace_id)
