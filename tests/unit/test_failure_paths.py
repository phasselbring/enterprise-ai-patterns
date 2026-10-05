import asyncio
import pytest

from enterprise_ai_patterns.agents.governed_tool_call import (
    ToolRequest, ToolResult, governed_execute, governed_execute_async
)
from enterprise_ai_patterns.rag.pipeline import Caller, Chunk, answer_question
from enterprise_ai_patterns.text_to_sql.safe_text_to_sql import validate_read_only_sql


class Policy:
    def __init__(self, allowed=True): self.allowed = allowed
    def authorize(self, request): return self.allowed


class Approvals:
    def __init__(self, required=False, approved=True):
        self._required = required
        self._approved = approved
    def required(self, request): return self._required
    def approved(self, request): return self._approved


class Executor:
    def __init__(self, verified=True): self.verified = verified
    def execute(self, request, *, idempotency_key):
        return ToolResult(True, {"ok": True}, "op-1")
    def verify(self, result): return self.verified


class AsyncExecutor:
    def __init__(self, verified=True): self.verified = verified
    async def execute(self, request, *, idempotency_key):
        return ToolResult(True, {"ok": True}, "op-1")
    async def verify(self, result): return self.verified


class Audit(list): pass


def req(): return ToolRequest("u1", "write", {"x": 1}, "trace")


def test_sync_approval_and_verification_fail_closed():
    with pytest.raises(PermissionError):
        governed_execute(req(), policy=Policy(), approvals=Approvals(True, False), executor=Executor(), audit=Audit())
    with pytest.raises(RuntimeError):
        governed_execute(req(), policy=Policy(), approvals=Approvals(), executor=Executor(False), audit=Audit())


def test_async_denial_approval_and_verification_fail_closed():
    async def run():
        with pytest.raises(PermissionError):
            await governed_execute_async(req(), policy=Policy(False), approvals=Approvals(), executor=AsyncExecutor(), audit=Audit())
        with pytest.raises(PermissionError):
            await governed_execute_async(req(), policy=Policy(), approvals=Approvals(True, False), executor=AsyncExecutor(), audit=Audit())
        with pytest.raises(RuntimeError):
            await governed_execute_async(req(), policy=Policy(), approvals=Approvals(), executor=AsyncExecutor(False), audit=Audit())
    asyncio.run(run())


def test_pipeline_rejects_fabricated_source_id():
    class Retriever:
        def search(self, query, *, limit=20):
            return [Chunk("real", "evidence", ("legal",), "x://real")]
    class Reranker:
        def rerank(self, query, chunks, *, limit=6): return list(chunks)
    class Generator:
        def answer(self, query, context): return "claim", ["invented"]
    class Trace:
        def record(self, event): pass

    with pytest.raises(ValueError):
        answer_question(
            caller=Caller("u1", ("legal",)), query="q", retriever=Retriever(),
            reranker=Reranker(), generator=Generator(), trace_sink=Trace()
        )


def test_multiple_sql_statements_are_rejected():
    with pytest.raises(ValueError, match="Multiple statements"):
        validate_read_only_sql("SELECT * FROM customers; SELECT * FROM orders")
