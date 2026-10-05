from enterprise_ai_patterns.rag.grounding import Claim, GeneratedAnswer, GroundingChecker
from enterprise_ai_patterns.rag.pipeline import Chunk


class Support:
    def supports(self, claim, evidence):
        return "30 days" in claim and "thirty days" in evidence


def test_grounding_rejects_unknown_citation():
    answer = GeneratedAnswer("x", (Claim("x", ("missing",)),))
    result = GroundingChecker().check(answer, [])
    assert result.ok is False
    assert result.invalid_source_ids == ("missing",)


def test_grounding_can_check_semantic_support_via_adapter():
    chunks = [Chunk("c1", "Either party may terminate with thirty days notice.", ("legal",), "x://1")]
    answer = GeneratedAnswer("30 days", (Claim("Termination requires 30 days notice", ("c1",)),))
    assert GroundingChecker(Support()).check(answer, chunks).ok is True
