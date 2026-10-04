from enterprise_ai_patterns.ai_sdlc.gates import Decision, Evidence, release_gate

def test_independent_review_is_required():
    evidence = Evidence(True, True, True, False, 0)
    assert release_gate(evidence) == Decision.REBASELINE

def test_high_risk_finding_holds_release():
    evidence = Evidence(True, True, True, True, 1)
    assert release_gate(evidence) == Decision.HOLD
