"""Independent execution boundary for registered, authorized async tools.

The gateway intentionally does not claim exactly-once side effects. Tool handlers
must independently enforce identity and downstream idempotency for writes.
"""
from collections.abc import Callable, Awaitable
from typing import Any
from .authorization import ExecutionPrincipal, require_authorized
from .approval import ApprovalVerifier, require_approval

class ExecutionGateway:
    def __init__(self, tools: dict[str, Callable[[dict[str, Any]], Awaitable[Any]]],
                 *, audit: Callable[[dict], None], approval_verifier: ApprovalVerifier | None = None,
                 protected_tools: frozenset[str] = frozenset()):
        self.tools = dict(tools)
        self.audit = audit
        self.approval_verifier = approval_verifier
        self.protected_tools = protected_tools

    async def execute(self, principal: ExecutionPrincipal, name: str, arguments: dict[str, Any],
                      *, action_id: str, resource_id: str = "") -> Any:
        try:
            require_authorized(principal, name)
            if name not in self.tools:
                raise PermissionError("tool not registered")
            if name in self.protected_tools:
                if self.approval_verifier is None:
                    raise PermissionError("independent approval verifier missing")
                require_approval(self.approval_verifier, caller_id=principal.caller_id,
                                 action_id=action_id, resource_id=resource_id)
            result = await self.tools[name](dict(arguments))
        except Exception as exc:
            self.audit({"event": "tool_blocked_or_failed", "caller": principal.caller_id,
                        "tool": name, "error": type(exc).__name__})
            raise
        self.audit({"event": "tool_completed", "caller": principal.caller_id, "tool": name})
        return result
