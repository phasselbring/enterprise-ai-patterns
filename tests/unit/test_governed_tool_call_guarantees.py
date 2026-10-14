import asyncio
from datetime import date

import pytest

from enterprise_ai_patterns.agents.governed_tool_call import (
    ApprovalRequired,
    ToolDenied,
    ToolExecutionError,
    ToolRequest,
    ToolResult,
    ToolVerificationError,
    governed_execute,
    governed_execute_async,
    idempotency_key,
)
from enterprise_ai_patterns.agents.tool_registry import LocalToolProvider, ToolDefinition


class Policy:
    def __init__(self, allowed=True): self.allowed = allowed
    def authorize(self, request): return self.allowed


class Approvals:
    def __init__(self, required=False, approved=True):
        self._required, self._approved = required, approved
    def required(self, request): return self._required
    def approved(self, request): return self._approved


class RecordingExecutor:
    def __init__(self): self.keys = []
    def execute(self, request, *, idempotency_key):
        self.keys.append(idempotency_key)
        return ToolResult(True, {}, "op")
    def verify(self, result): return True


class RaisingExecutor:
    def execute(self, request, *, idempotency_key): raise ConnectionError("db down")
    def verify(self, result): return True


class RaisingVerifierExecutor:
    def execute(self, request, *, idempotency_key): return ToolResult(True, {}, "op")
    def verify(self, result): raise TimeoutError("verifier timed out")


class AsyncRaisingExecutor:
    async def execute(self, request, *, idempotency_key): raise ConnectionError("db down")
    async def verify(self, result): return True


def test_retry_with_new_trace_id_reuses_idempotency_key():
    first = ToolRequest("u1", "create_order", {"sku": "A"}, "trace-1")
    retry = ToolRequest("u1", "create_order", {"sku": "A"}, "trace-2")
    assert idempotency_key(first) == idempotency_key(retry)


def test_key_distinguishes_caller_tool_and_arguments():
    base = ToolRequest("u1", "create_order", {"sku": "A"}, "t")
    assert idempotency_key(base) != idempotency_key(ToolRequest("u2", "create_order", {"sku": "A"}, "t"))
    assert idempotency_key(base) != idempotency_key(ToolRequest("u1", "cancel_order", {"sku": "A"}, "t"))
    assert idempotency_key(base) != idempotency_key(ToolRequest("u1", "create_order", {"sku": "B"}, "t"))


def test_explicit_idempotency_key_wins():
    request = ToolRequest("u1", "t", {}, "trace", idempotency_key="session-1:step-3")
    executor = RecordingExecutor()
    governed_execute(request, policy=Policy(), approvals=Approvals(), executor=executor, audit=[])
    assert executor.keys == ["session-1:step-3"]


def test_non_json_arguments_do_not_crash_key_derivation():
    request = ToolRequest("u1", "t", {"day": date(2026, 1, 2)}, "trace")
    assert len(idempotency_key(request)) == 64


def test_error_types_are_specific_but_backward_compatible():
    assert issubclass(ToolDenied, PermissionError)
    assert issubclass(ApprovalRequired, PermissionError)
    assert issubclass(ToolVerificationError, RuntimeError)
    assert issubclass(ToolExecutionError, RuntimeError)
    with pytest.raises(ToolDenied):
        governed_execute(ToolRequest("u", "t", {}, "x"), policy=Policy(False),
                         approvals=Approvals(), executor=RecordingExecutor(), audit=[])
    with pytest.raises(ApprovalRequired):
        governed_execute(ToolRequest("u", "t", {}, "x"), policy=Policy(),
                         approvals=Approvals(True, False), executor=RecordingExecutor(), audit=[])


def test_executor_exception_is_audited_and_wrapped():
    audit = []
    with pytest.raises(ToolExecutionError) as info:
        governed_execute(ToolRequest("u", "t", {}, "trace-9"), policy=Policy(),
                         approvals=Approvals(), executor=RaisingExecutor(), audit=audit)
    assert isinstance(info.value.__cause__, ConnectionError)
    assert audit[-1]["event"] == "tool_failed"
    assert audit[-1]["trace_id"] == "trace-9"
    assert audit[-1]["error_type"] == "ConnectionError"


def test_verifier_exception_is_audited_and_fails_closed():
    audit = []
    with pytest.raises(ToolVerificationError):
        governed_execute(ToolRequest("u", "t", {}, "trace"), policy=Policy(),
                         approvals=Approvals(), executor=RaisingVerifierExecutor(), audit=audit)
    assert audit[-1]["event"] == "tool_verification_failed"


def test_async_executor_exception_is_audited():
    audit = []
    with pytest.raises(ToolExecutionError):
        asyncio.run(governed_execute_async(ToolRequest("u", "t", {}, "trace"), policy=Policy(),
                                           approvals=Approvals(), executor=AsyncRaisingExecutor(),
                                           audit=audit))
    assert audit[-1]["event"] == "tool_failed"


def test_audit_events_carry_caller_tool_and_key():
    audit = []
    governed_execute(ToolRequest("u1", "lookup", {}, "trace"), policy=Policy(),
                     approvals=Approvals(), executor=RecordingExecutor(), audit=audit)
    event = audit[-1]
    assert event["caller_id"] == "u1"
    assert event["tool_name"] == "lookup"
    assert event["idempotency_key"]


def test_local_provider_operation_ids_are_unique_per_call():
    async def run():
        provider = LocalToolProvider()
        async def handler(args): return {}
        provider.register(ToolDefinition("lookup", "", {}), handler)
        first = await provider.call_tool("lookup", {})
        second = await provider.call_tool("lookup", {})
        return first.operation_id, second.operation_id
    first, second = asyncio.run(run())
    assert first != second
    assert first.startswith("local:lookup:")


def test_async_verifier_exception_is_audited_and_fails_closed():
    class Executor:
        async def execute(self, request, *, idempotency_key): return ToolResult(True, {}, "op")
        async def verify(self, result): raise TimeoutError("slow")
    audit = []
    with pytest.raises(ToolVerificationError):
        asyncio.run(governed_execute_async(ToolRequest("u", "t", {}, "trace"), policy=Policy(),
                                           approvals=Approvals(), executor=Executor(), audit=audit))
    assert audit[-1]["event"] == "tool_verification_failed"
    assert audit[-1]["error_type"] == "TimeoutError"
