from dataclasses import dataclass
from enum import Enum

class Decision(str, Enum):
    CONTINUE = "continue"
    HOLD = "hold"
    REBASELINE = "rebaseline"

@dataclass(frozen=True)
class Evidence:
    tests_passed: bool
    security_scan_passed: bool
    traceability_complete: bool
    independent_reviewer: bool
    unresolved_high_risk_findings: int

def release_gate(evidence: Evidence):
    if evidence.unresolved_high_risk_findings:
        return Decision.HOLD
    ok = (
        evidence.tests_passed
        and evidence.security_scan_passed
        and evidence.traceability_complete
        and evidence.independent_reviewer
    )
    return Decision.CONTINUE if ok else Decision.REBASELINE
