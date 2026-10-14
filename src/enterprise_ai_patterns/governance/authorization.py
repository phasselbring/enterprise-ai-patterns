"""Server-defined allowlist policy; request identity must already be verified."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionPrincipal:
    caller_id: str
    permitted_tools: frozenset[str]

class AuthorizationDenied(PermissionError):
    pass

def require_authorized(principal: ExecutionPrincipal, tool_name: str) -> None:
    if not principal.caller_id or tool_name not in principal.permitted_tools:
        raise AuthorizationDenied("tool not authorized")
