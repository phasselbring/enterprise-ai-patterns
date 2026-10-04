from dataclasses import dataclass
from typing import Any
import hashlib, json

@dataclass(frozen=True)
class ToolRequest:
    caller_id: str
    tool_name: str
    arguments: dict[str, Any]
    trace_id: str

@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: dict[str, Any]
    operation_id: str

def _key(request):
    payload = json.dumps(request.__dict__, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()

def governed_execute(request, *, policy, approvals, executor, audit):
    if not policy.authorize(request):
        audit.append({"event": "tool_denied", "trace_id": request.trace_id})
        raise PermissionError("denied")

    if approvals.required(request) and not approvals.approved(request):
        audit.append({"event": "approval_required", "trace_id": request.trace_id})
        raise PermissionError("approval required")

    result = executor.execute(request, idempotency_key=_key(request))
    if not result.ok or not executor.verify(result):
        audit.append({"event": "tool_verification_failed", "trace_id": request.trace_id})
        raise RuntimeError("verification failed")

    audit.append({
        "event": "tool_completed",
        "trace_id": request.trace_id,
        "operation_id": result.operation_id,
    })
    return result
