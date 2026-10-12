"""Failure-mode behaviour of the agent loop: denials, errors, approvals, resume and budgets."""

import asyncio

import pytest

from enterprise_ai_patterns.agents.governed_tool_call import ApprovalRequired, ToolRequest
from enterprise_ai_patterns.agents.loop import (
    AgentDecision,
    AgentLoop,
    DecisionKind,
    RegistryExecutor,
    SessionCompletedError,
    StepBudgetExceeded,
)
from enterprise_ai_patterns.agents.state import InMemoryStateStore
from enterprise_ai_patterns.agents.tool_registry import LocalToolProvider, ToolDefinition, ToolRegistry


def tool(name, **args):
    return AgentDecision(DecisionKind.TOOL, name, args)


def final(answer="done"):
    return AgentDecision(DecisionKind.FINAL, answer=answer)


class ScriptedModel:
    def __init__(self, *decisions):
        self.decisions = list(decisions)
        self.turns = []

    async def decide(self, turn):
        self.turns.append(turn)
        return self.decisions.pop(0)


class ContextLoader:
    async def load(self, *, caller_id, goal):
        return {"owner": caller_id, "private_note": f"{caller_id} only"}


class Policy:
    def authorize(self, request):
        return request.tool_name != "forbidden"


class Approvals:
    def __init__(self):
        self.granted = False

    def required(self, request):
        return request.tool_name == "place_order"

    def approved(self, request):
        return self.granted


class Verifier:
    async def verify(self, result):
        return result.ok


class Harness:
    def __init__(self, max_steps=8):
        self.calls = []
        self.audit = []
        self.store = InMemoryStateStore()
        self.approvals = Approvals()
        self.max_steps = max_steps
        provider = LocalToolProvider()

        async def lookup(args):
            self.calls.append(("lookup", args))
            return {"value": 42}

        async def place_order(args):
            self.calls.append(("place_order", args))
            return {"order": "o-1"}

        async def flaky(args):
            self.calls.append(("flaky", args))
            raise ConnectionError("db down")

        for name, handler in [("lookup", lookup), ("place_order", place_order), ("flaky", flaky)]:
            provider.register(ToolDefinition(name, name, {"type": "object"}), handler)
        # "forbidden" is discoverable but policy denies it
        async def forbidden(args):
            self.calls.append(("forbidden", args))
            return {}
        provider.register(ToolDefinition("forbidden", "forbidden", {"type": "object"}), forbidden)
        self.registry = ToolRegistry([provider])

    def loop(self, model):
        return AgentLoop(
            model=model,
            context_loader=ContextLoader(),
            tool_registry=self.registry,
            state_store=self.store,
            policy=Policy(),
            approvals=self.approvals,
            verifier=Verifier(),
            audit=self.audit,
            max_steps=self.max_steps,
        )

    def run(self, model, *, session_id="s1", caller_id="alice", goal="g"):
        return asyncio.run(self.loop(model).run(session_id=session_id, caller_id=caller_id, goal=goal))

    def kinds(self, session_id="s1"):
        return [e.kind for e in self.store.load(session_id).events]


def test_denied_tool_is_reported_to_model_which_can_recover():
    h = Harness()
    model = ScriptedModel(tool("forbidden"), final("recovered"))
    assert h.run(model) == "recovered"
    assert ("forbidden", {}) not in h.calls
    assert h.kinds() == ["tool_error", "final"]
    error = model.turns[1].prior_events[0]
    assert error.data["tool"] == "forbidden" and error.data["error"] == "denied"
    assert any(e["event"] == "tool_denied" for e in h.audit)


def test_unknown_tool_is_reported_not_crashing():
    h = Harness()
    model = ScriptedModel(tool("no_such_tool"), final())
    h.run(model)
    assert h.store.load("s1").events[0].data["error"] == "unknown_tool"


def test_malformed_tool_decision_is_reported_not_crashing():
    h = Harness()
    model = ScriptedModel(AgentDecision(DecisionKind.TOOL), final())
    h.run(model)
    assert h.kinds() == ["tool_error", "final"]


def test_tool_exception_is_audited_and_reported():
    h = Harness()
    model = ScriptedModel(tool("flaky"), final("gave up gracefully"))
    assert h.run(model) == "gave up gracefully"
    assert h.store.load("s1").events[0].data["error"] == "execution_failed"
    assert any(e["event"] == "tool_failed" for e in h.audit)


def test_approval_pauses_session_then_resumes_after_grant():
    h = Harness()
    with pytest.raises(ApprovalRequired):
        h.run(ScriptedModel(tool("place_order", sku="A")))
    assert h.kinds() == ["awaiting_approval"]
    assert not h.store.load("s1").completed
    assert h.calls == []

    h.approvals.granted = True
    assert h.run(ScriptedModel(tool("place_order", sku="A"), final("ordered"))) == "ordered"
    assert h.calls == [("place_order", {"sku": "A"})]
    assert h.kinds() == ["awaiting_approval", "tool_result", "final"]


def test_other_caller_cannot_resume_session():
    h = Harness()
    h.run(ScriptedModel(tool("lookup"), final()), caller_id="alice")
    intruder = ScriptedModel(final("stolen"))
    with pytest.raises(PermissionError):
        h.run(intruder, caller_id="mallory")
    assert intruder.turns == []
    assert any(e["event"] == "session_access_denied" for e in h.audit)


def test_in_progress_session_also_rejects_other_caller():
    h = Harness()
    with pytest.raises(ApprovalRequired):
        h.run(ScriptedModel(tool("place_order")), caller_id="alice")
    intruder = ScriptedModel(final())
    with pytest.raises(PermissionError):
        h.run(intruder, caller_id="mallory")
    assert intruder.turns == []


def test_completed_session_is_not_rerun():
    h = Harness()
    h.run(ScriptedModel(final("first")))
    again = ScriptedModel(final("second"))
    with pytest.raises(SessionCompletedError):
        h.run(again)
    assert again.turns == []
    assert h.kinds() == ["final"]


def test_resume_with_different_goal_is_rejected():
    h = Harness()
    with pytest.raises(ApprovalRequired):
        h.run(ScriptedModel(tool("place_order")), goal="order widgets")
    with pytest.raises(ValueError, match="goal"):
        h.run(ScriptedModel(final()), goal="something else")


def test_step_budget_is_enforced_across_runs():
    h = Harness(max_steps=3)
    with pytest.raises(StepBudgetExceeded):
        h.run(ScriptedModel(*[tool("lookup", i=i) for i in range(10)]))
    assert len(h.calls) == 3

    second = ScriptedModel(*[tool("lookup", i=i) for i in range(10)])
    with pytest.raises(StepBudgetExceeded):
        h.run(second)
    assert len(h.calls) == 3
    assert second.turns == []


def test_step_budget_error_is_still_a_runtime_error():
    assert issubclass(StepBudgetExceeded, RuntimeError)


def test_tool_calls_get_session_scoped_idempotency_keys():
    h = Harness()
    h.run(ScriptedModel(tool("lookup", q=1), tool("lookup", q=1), final()))
    keys = [e["idempotency_key"] for e in h.audit if e["event"] == "tool_completed"]
    assert len(keys) == 2 and keys[0] != keys[1]
    assert all(k.startswith("s1:") for k in keys)


def test_registry_executor_replays_result_for_repeated_key():
    async def run():
        calls = []
        provider = LocalToolProvider()
        async def handler(args):
            calls.append(args)
            return {"n": len(calls)}
        provider.register(ToolDefinition("t", "", {}), handler)
        registry = ToolRegistry([provider])
        await registry.boot()
        executor = RegistryExecutor(registry, Verifier())
        request = ToolRequest("u", "t", {}, "trace")
        first = await executor.execute(request, idempotency_key="k1")
        replay = await executor.execute(request, idempotency_key="k1")
        fresh = await executor.execute(request, idempotency_key="k2")
        return calls, first, replay, fresh
    calls, first, replay, fresh = asyncio.run(run())
    assert len(calls) == 2
    assert replay == first
    assert fresh.data == {"n": 2}


def test_failed_verification_is_reported_to_model():
    h = Harness()

    class RejectingVerifier:
        async def verify(self, result): return False

    loop = AgentLoop(model=ScriptedModel(tool("lookup"), AgentDecision(DecisionKind.ABSTAIN)),
                     context_loader=ContextLoader(), tool_registry=h.registry, state_store=h.store,
                     policy=Policy(), approvals=h.approvals, verifier=RejectingVerifier(),
                     audit=h.audit)
    answer = asyncio.run(loop.run(session_id="s1", caller_id="alice", goal="g"))
    assert answer == "insufficient evidence"
    assert h.kinds() == ["tool_error", "abstain"]
    assert h.store.load("s1").events[0].data["error"] == "verification_failed"
    assert h.store.load("s1").completed


def test_max_steps_must_be_positive():
    h = Harness(max_steps=0)
    with pytest.raises(ValueError):
        h.loop(ScriptedModel())
