from __future__ import annotations

from dataclasses import dataclass
import time
import uuid

from .grounding import GeneratedAnswer, GroundingChecker
from .pipeline import Caller, Chunk
from .post_retrieval import ContextBuilder
from .pre_retrieval import QueryPlanner


@dataclass(frozen=True)
class ProductionAnswer:
    text: str
    citations: tuple[str, ...]
    trace_id: str


class GroundingError(RuntimeError):
    pass


class ProductionRAGPipeline:
    """Composes pre-retrieval, retrieval, filtering, reranking, generation and grounding."""

    def __init__(
        self,
        *,
        planner: QueryPlanner,
        retriever,
        reranker,
        context_builder: ContextBuilder,
        generator,
        grounding_checker: GroundingChecker,
        trace_sink,
        router=None,
    ) -> None:
        self._planner = planner
        self._retriever = retriever
        self._reranker = reranker
        self._context_builder = context_builder
        self._generator = generator
        self._grounding_checker = grounding_checker
        self._trace_sink = trace_sink
        self._router = router

    def run(self, *, caller: Caller, query: str) -> ProductionAnswer:
        trace_id = str(uuid.uuid4())
        started = time.perf_counter()
        plan = self._planner.plan(query)

        # Query expansion can improve recall. Merge candidates across rewrites/decompositions.
        candidate_by_id: dict[str, Chunk] = {}
        routed = (self._planner.routed_queries(plan)
                  if self._router is not None else ())
        if self._router is not None and not routed:
            raise ValueError("Configured router requires a planner with routed_queries()")
        for index, retrieval_query in enumerate(plan.retrieval_queries):
            # Source selection is deterministic; the selected backend must enforce
            # both caller ACLs and metadata restrictions before top-k.
            matches = (self._router.search(routed[index], caller=caller, limit=20,
                                           metadata_filters=plan.metadata_filters)
                       if self._router is not None else
                       self._retriever.search(retrieval_query, limit=20, caller=caller))
            for chunk in matches:
                current = candidate_by_id.get(chunk.chunk_id)
                if current is None or chunk.retrieval_score > current.retrieval_score:
                    candidate_by_id[chunk.chunk_id] = chunk

        candidates = list(candidate_by_id.values())

        # Defense in depth: check again after ACL-aware retrieval, never rely on the LLM.
        permitted = [
            chunk for chunk in candidates
            if set(caller.groups).intersection(chunk.allowed_groups)
        ]

        reranked = self._reranker.rerank(plan.normalized_query, permitted, limit=6)
        context = self._context_builder.build(reranked)
        generated: GeneratedAnswer = self._generator.generate(
            query=plan.normalized_query,
            context=context,
            intent=plan.intent,
        )

        grounding = self._grounding_checker.check(generated, context.chunks)
        if not grounding.ok:
            raise GroundingError(
                f"grounding failed: invalid_sources={grounding.invalid_source_ids}; "
                f"unsupported_claims={grounding.unsupported_claims}"
            )

        cited_ids = tuple(
            dict.fromkeys(
                source_id
                for claim in generated.claims
                for source_id in claim.source_ids
            )
        )
        source_map = {c.chunk_id: c.source_uri for c in context.chunks}
        citations = tuple(source_map[source_id] for source_id in cited_ids)

        self._trace_sink.record({
            "trace_id": trace_id,
            "intent": plan.intent,
            "retrieval_queries": len(plan.retrieval_queries),
            "candidate_count": len(candidates),
            "authorized_count": len(permitted),
            "reranked_count": len(reranked),
            "context_count": len(context.chunks),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        })

        return ProductionAnswer(generated.text, citations, trace_id)
