import asyncio
import pytest
from enterprise_ai_patterns.harnesses.contracts import HarnessRequest, HarnessResult
from enterprise_ai_patterns.governance.authorization import ExecutionPrincipal, AuthorizationDenied
from enterprise_ai_patterns.governance.execution_gateway import ExecutionGateway
from enterprise_ai_patterns.validation.scenario import Scenario
from enterprise_ai_patterns.validation.runner import run_scenario
from enterprise_ai_patterns.validation.fault_injection import FailingTool, InjectedToolFailure

class FakeHarness:
    async def run(self, request):
        return HarnessResult("fake", "offline", "completed", "22 units; 12 days")

def test_contract_invalid_budget():
    with pytest.raises(ValueError):
        HarnessRequest("task", "session", "caller", "prompt", max_steps=0)

def test_scenario_pass():
    _, checks, card = asyncio.run(run_scenario(FakeHarness(), Scenario("shortage", "query", expected_text=("22", "12"))))
    assert all(checks.values()) and card.accepted

def test_gateway_blocks_denial_before_handler():
    events, called = [], []
    async def handler(args):
        called.append(args)
        return {"ok": True}
    gateway = ExecutionGateway({"write": handler}, audit=events.append)
    with pytest.raises(AuthorizationDenied):
        asyncio.run(gateway.execute(ExecutionPrincipal("alice", frozenset()), "write", {}, action_id="a"))
    assert not called and events[0]["event"] == "tool_blocked_or_failed"

def test_gateway_requires_independent_approval():
    events, called = [], []
    async def handler(args):
        called.append(1)
    gateway = ExecutionGateway({"write": handler}, audit=events.append, protected_tools=frozenset({"write"}))
    with pytest.raises(PermissionError):
        asyncio.run(gateway.execute(ExecutionPrincipal("alice", frozenset({"write"})), "write", {}, action_id="a"))
    assert not called

def test_fault_injection_audited():
    events = []
    failing = FailingTool()
    gateway = ExecutionGateway({"read": failing}, audit=events.append)
    with pytest.raises(InjectedToolFailure):
        asyncio.run(gateway.execute(ExecutionPrincipal("alice", frozenset({"read"})), "read", {}, action_id="a"))
    assert failing.calls == 1 and events[0]["error"] == "InjectedToolFailure"
