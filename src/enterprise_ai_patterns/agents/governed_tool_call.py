"""Policy -> approval -> idempotent execution -> verification -> audit, for every tool call.

Every outcome is audited, including executor and verifier failures, and every failure raises a
specific exception so callers (such as the agent loop) can react without string matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Protocol
import hashlib
import json


@dataclass(frozen=True)
class ToolRequest:
    caller_id: str
    tool_name: str
    arguments: dict[str, Any]
    trace_id: str
    # Callers that know the logical operation (e.g. session + step) should set this explicitly.
    # Otherwise it is derived from caller, tool and arguments; never from the per-attempt trace_id,
    # so a retry of the same operation produces the same key.
    idempotency_key: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any]
    operation_id: str


class ToolDenied(PermissionError):
    """Policy refused the call. The tool did not run."""


class ApprovalRequired(PermissionError):
    """The call needs a human approval that has not been granted yet. The tool did not run."""


class ToolExecutionError(RuntimeError):
    """The executor raised. Whether the side effect happened is unknown; retry with the same key."""


class ToolVerificationError(RuntimeError):
    """The tool ran but its result failed verification (or the verifier itself failed)."""


class Policy(Protocol):
    def authorize(self, request: ToolRequest) -> bool: ...


class Approvals(Protocol):
    def required(self, request: ToolRequest) -> bool: ...
    def approved(self, request: ToolRequest) -> bool: ...


class Executor(Protocol):
    def execute(self, request: ToolRequest, *, idempotency_key: str) -> ToolResult: ...
    def verify(self, result: ToolResult) -> bool: ...


class AsyncExecutor(Protocol):
    def execute(self, request: ToolRequest, *, idempotency_key: str) -> Awaitable[ToolResult]: ...
    def verify(self, result: ToolResult) -> Awaitable[bool]: ...


class AuditSink(Protocol):
    def append(self, event: dict[str, Any]) -> None: ...


def idempotency_key(request: ToolRequest) -> str:
    if request.idempotency_key:
        return request.idempotency_key
    payload = json.dumps(
        {"caller_id": request.caller_id, "tool_name": request.tool_name, "arguments": request.arguments},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


# Backward-compatible private alias.
_key = idempotency_key


def _event(name: str, request: ToolRequest, key: str, **extra: Any) -> dict[str, Any]:
    return {
        "event": name,
        "trace_id": request.trace_id,
        "caller_id": request.caller_id,
        "tool_name": request.tool_name,
        "idempotency_key": key,
        **extra,
    }


def _preflight(request: ToolRequest, policy: Policy, approvals: Approvals, audit: AuditSink) -> str:
    key = idempotency_key(request)
    if not policy.authorize(request):
        audit.append(_event("tool_denied", request, key))
        raise ToolDenied("denied")
    if approvals.required(request) and not approvals.approved(request):
        audit.append(_event("approval_required", request, key))
        raise ApprovalRequired("approval required")
    return key


def _execution_failed(request: ToolRequest, key: str, audit: AuditSink, exc: Exception) -> ToolExecutionError:
    audit.append(_event("tool_failed", request, key, error_type=type(exc).__name__))
    return ToolExecutionError(f"tool execution failed: {type(exc).__name__}")


def _verification_failed(
    request: ToolRequest, key: str, audit: AuditSink, result: ToolResult | None, exc: Exception | None = None
) -> ToolVerificationError:
    extra: dict[str, Any] = {}
    if result is not None:
        extra["operation_id"] = result.operation_id
    if exc is not None:
        extra["error_type"] = type(exc).__name__
    audit.append(_event("tool_verification_failed", request, key, **extra))
    return ToolVerificationError("verification failed")


def _completed(request: ToolRequest, key: str, audit: AuditSink, result: ToolResult) -> ToolResult:
    audit.append(_event("tool_completed", request, key, operation_id=result.operation_id))
    return result


def governed_execute(request, *, policy, approvals, executor, audit):
    key = _preflight(request, policy, approvals, audit)

    try:
        result = executor.execute(request, idempotency_key=key)
    except Exception as exc:
        raise _execution_failed(request, key, audit, exc) from exc

    try:
        verified = result.ok and executor.verify(result)
    except Exception as exc:
        raise _verification_failed(request, key, audit, result, exc) from exc
    if not verified:
        raise _verification_failed(request, key, audit, result)

    return _completed(request, key, audit, result)


async def governed_execute_async(request, *, policy, approvals, executor, audit):
    """Async equivalent used by agent loops and remote/MCP tools."""
    key = _preflight(request, policy, approvals, audit)

    try:
        result = await executor.execute(request, idempotency_key=key)
    except Exception as exc:
        raise _execution_failed(request, key, audit, exc) from exc

    try:
        verified = result.ok and await executor.verify(result)
    except Exception as exc:
        raise _verification_failed(request, key, audit, result, exc) from exc
    if not verified:
        raise _verification_failed(request, key, audit, result)

    return _completed(request, key, audit, result)
