from enterprise_ai_patterns.rag.grounding import Claim, GeneratedAnswer, GroundingChecker
from enterprise_ai_patterns.rag.pipeline import Caller, Chunk
from enterprise_ai_patterns.rag.post_retrieval import ContextBuilder
from enterprise_ai_patterns.rag.pre_retrieval import BasicQueryPlanner
from enterprise_ai_patterns.rag.production_pipeline import ProductionRAGPipeline
from enterprise_ai_patterns.rag.reranker import TokenOverlapReranker


class Retriever:
    def search(self, query, *, limit=20):
        return [
            Chunk("term", "Either party may terminate with thirty days written notice.", ("legal",), "contract://msa-42/12.4", retrieval_score=0.5),
            Chunk("secret", "Restricted finance terms.", ("finance",), "contract://secret", retrieval_score=0.9),
        ]


class Generator:
    def generate(self, *, query, context, intent):
        assert [c.chunk_id for c in context.chunks] == ["term"]
        return GeneratedAnswer(
            "Yes. Either party may terminate with 30 days written notice.",
            (Claim("Either party may terminate with 30 days written notice.", ("term",)),),
        )


class Support:
    def supports(self, claim, evidence): return "terminate" in claim.lower() and "terminate" in evidence.lower()


class Trace:
    def __init__(self): self.events = []
    def record(self, event): self.events.append(event)


def test_full_rag_flow_filters_reranks_generates_and_verifies():
    trace = Trace()
    pipeline = ProductionRAGPipeline(
        planner=BasicQueryPlanner(intent_classifier=lambda q: "contract_review"),
        retriever=Retriever(),
        reranker=TokenOverlapReranker(),
        context_builder=ContextBuilder(),
        generator=Generator(),
        grounding_checker=GroundingChecker(Support()),
        trace_sink=trace,
    )
    answer = pipeline.run(caller=Caller("lawyer-1", ("legal",)), query="termination notice")
    assert answer.citations == ("contract://msa-42/12.4",)
    assert trace.events[0]["authorized_count"] == 1
