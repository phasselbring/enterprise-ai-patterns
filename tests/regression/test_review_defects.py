"""One regression test per defect from the governance/security review.

These tests use only interfaces that existed before the fix, so they can be run against the old
code to demonstrate each defect (they fail there) and against the fixed code (they pass).
Detailed coverage of each fix lives in the dedicated test modules.
"""

import asyncio

import pytest

from enterprise_ai_patterns.agents.governed_tool_call import (
    ToolRequest,
    ToolResult,
    _key,
    governed_execute,
)
from enterprise_ai_patterns.agents.loop import AgentDecision, AgentLoop, DecisionKind, RegistryExecutor
from enterprise_ai_patterns.agents.state import InMemoryStateStore
from enterprise_ai_patterns.agents.tool_registry import LocalToolProvider, ToolDefinition, ToolRegistry
from enterprise_ai_patterns.rag.pipeline import Chunk
from enterprise_ai_patterns.rag.post_retrieval import ContextBuilder
from enterprise_ai_patterns.text_to_sql.safe_text_to_sql import (
    validate_read_only_sql,
    validate_table_allowlist,
)


# ---------------------------------------------------------------- shared fakes


class Policy:
    def authorize(self, request): return request.tool_name != "forbidden"


class Approvals:
    def required(self, request): return False
    def approved(self, request): return True


class Verifier:
    async def verify(self, result): return result.ok


class ContextLoader:
    async def load(self, *, caller_id, goal): return {"private_note": f"{caller_id} only"}


class ScriptedModel:
    def __init__(self, *decisions):
        self.decisions, self.turns = list(decisions), []

    async def decide(self, turn):
        self.turns.append(turn)
        return self.decisions.pop(0)


def make_loop(model, store, *, max_steps=8, audit=None):
    provider = LocalToolProvider()

    async def handler(args): return {"value": 1}

    for name in ("lookup", "forbidden"):
        provider.register(ToolDefinition(name, name, {"type": "object"}), handler)
    return AgentLoop(model=model, context_loader=ContextLoader(), tool_registry=ToolRegistry([provider]),
                     state_store=store, policy=Policy(), approvals=Approvals(), verifier=Verifier(),
                     audit=audit if audit is not None else [], max_steps=max_steps)


def run(loop, *, session_id="s1", caller_id="alice", goal="g"):
    return asyncio.run(loop.run(session_id=session_id, caller_id=caller_id, goal=goal))


def validate(sql):
    validate_read_only_sql(sql)
    validate_table_allowlist(sql)


# ---------------------------------------------------------------- 1. text-to-SQL bypass


@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers, users",
    'SELECT * FROM "users"',
    "SELECT pg_read_file('/etc/passwd') FROM customers",
    "SELECT pg_sleep(100000) FROM customers",
])
def test_defect1_sql_guard_rejects_bypasses(sql):
    with pytest.raises(ValueError):
        validate(sql)


@pytest.mark.parametrize("sql", [
    "SELECT\n  id\nFROM customers",
    "WITH recent AS (SELECT customer_id FROM orders) SELECT * FROM recent",
])
def test_defect1_sql_guard_accepts_legitimate_queries(sql):
    validate(sql)


# ---------------------------------------------------------------- 2. idempotency


def test_defect2_retry_with_new_trace_id_keeps_idempotency_key():
    assert _key(ToolRequest("u", "create_order", {"sku": "A"}, "trace-1")) == \
        _key(ToolRequest("u", "create_order", {"sku": "A"}, "trace-2"))


def test_defect2_registry_executor_honours_idempotency_key():
    async def scenario():
        calls = []
        provider = LocalToolProvider()

        async def handler(args):
            calls.append(args)
            return {}

        provider.register(ToolDefinition("create_order", "", {}), handler)
        registry = ToolRegistry([provider])
        await registry.boot()
        executor = RegistryExecutor(registry, Verifier())
        request = ToolRequest("u", "create_order", {"sku": "A"}, "trace")
        await executor.execute(request, idempotency_key="same")
        await executor.execute(request, idempotency_key="same")
        return calls

    assert len(asyncio.run(scenario())) == 1


# ---------------------------------------------------------------- 3. denial crashes the loop


def test_defect3_denied_tool_is_fed_back_and_model_recovers():
    store = InMemoryStateStore()
    model = ScriptedModel(AgentDecision(DecisionKind.TOOL, "forbidden"),
                          AgentDecision(DecisionKind.FINAL, answer="recovered"))
    assert run(make_loop(model, store)) == "recovered"
    assert [e.kind for e in store.load("s1").events][-1] == "final"


# ---------------------------------------------------------------- 4. session resume


def test_defect4_other_caller_cannot_resume_session():
    store = InMemoryStateStore()
    run(make_loop(ScriptedModel(AgentDecision(DecisionKind.FINAL, answer="ok")), store), caller_id="alice")
    intruder = ScriptedModel(AgentDecision(DecisionKind.FINAL, answer="stolen"))
    with pytest.raises(PermissionError):
        run(make_loop(intruder, store), caller_id="mallory")
    assert intruder.turns == []  # never saw alice's goal or boot context


def test_defect4_step_budget_spans_runs():
    store = InMemoryStateStore()
    calls = 0
    for _ in range(2):
        model = ScriptedModel(*[AgentDecision(DecisionKind.TOOL, "lookup", {"i": i}) for i in range(10)])
        with pytest.raises(RuntimeError):
            run(make_loop(model, store, max_steps=3), caller_id="alice")
        calls += len(model.turns)
    assert calls == 3


# ---------------------------------------------------------------- 5. failures skip the audit


def test_defect5_executor_exception_is_audited():
    class RaisingExecutor:
        def execute(self, request, *, idempotency_key): raise ConnectionError("db down")
        def verify(self, result): return True

    audit = []
    with pytest.raises(Exception):
        governed_execute(ToolRequest("u", "t", {}, "trace-9"), policy=Policy(), approvals=Approvals(),
                         executor=RaisingExecutor(), audit=audit)
    assert [e["event"] for e in audit] == ["tool_failed"]


# ---------------------------------------------------------------- 6. operation_id


def test_defect6_operation_id_is_unique_per_call():
    async def scenario():
        provider = LocalToolProvider()

        async def handler(args): return {}

        provider.register(ToolDefinition("lookup", "", {}), handler)
        return [(await provider.call_tool("lookup", {})).operation_id for _ in range(2)]

    first, second = asyncio.run(scenario())
    assert first != second


# ---------------------------------------------------------------- 7. ContextBuilder


def test_defect7_oversized_chunk_does_not_drop_the_rest():
    chunks = [Chunk("big", "x" * 500, ("g",), "x://big"), Chunk("small", "fits", ("g",), "x://small")]
    assert [c.chunk_id for c in ContextBuilder(max_chars=100).build(chunks).chunks] == ["small"]
