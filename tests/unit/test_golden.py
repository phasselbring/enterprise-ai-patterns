from enterprise_ai_patterns.evaluation.golden import GoldenCase, Observation, evaluate_case


def test_golden_case_checks_retrieval_citations_and_label():
    case = GoldenCase(
        "c1", "q", ("clause-1",), ("secret-1",), "termination", False
    )
    obs = Observation(("clause-1", "other"), ("clause-1",), "termination", False)
    result = evaluate_case(case, obs, k=2)
    assert result["passed"] is True
    assert result["recall_at_k"] == 1.0
