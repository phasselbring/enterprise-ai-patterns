from enterprise_ai_patterns.evaluation.golden import GoldenCase, Observation, evaluate_case


def test_golden_case_fails_when_required_clause_is_missed():
    case = GoldenCase("liability", "Is IP indemnity uncapped?", ("msa-42:10.2",))
    obs = Observation(("msa-42:3.1",), ())
    result = evaluate_case(case, obs, k=5)
    assert result["passed"] is False
    assert result["recall_at_k"] == 0.0
