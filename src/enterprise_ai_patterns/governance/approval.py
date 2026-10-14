"""Fail-closed approval contract. A caller-supplied boolean is never sufficient."""
from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class ApprovalDecision:
    principal_id: str
    action_id: str
    resource_id: str
    authorized: bool

class ApprovalVerifier(Protocol):
    def verify(self, *, caller_id: str, action_id: str, resource_id: str) -> bool: ...

class ApprovalDenied(PermissionError):
    pass

def require_approval(verifier: ApprovalVerifier, *, caller_id: str, action_id: str, resource_id: str) -> None:
    if not verifier.verify(caller_id=caller_id, action_id=action_id, resource_id=resource_id):
        raise ApprovalDenied("approval required")
