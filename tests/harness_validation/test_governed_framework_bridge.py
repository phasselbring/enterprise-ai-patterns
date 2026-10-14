"""Offline cross-harness parity tests: no API keys or network needed."""
import json
from dataclasses import dataclass

import pytest

from enterprise_ai_patterns.agents.tool_registry import ToolDefinition, ToolRegistry
from enterprise_ai_patterns.governance.authorization import ExecutionPrincipal
from enterprise_ai_patterns.governance.execution_gateway import ExecutionGateway
from enterprise_ai_patterns.governance.framework_bridge import GovernedToolBridge


@dataclass
class Recorder:
    calls: int = 0

    async def handle(self, arguments):
        self.calls += 1
        return {"record": arguments["order_id"]}


@pytest.fixture
def fixture():
    recorder = Recorder()
    audit = []
    gateway = ExecutionGateway({"lookup_order": recorder.handle}, audit=audit.append)
    allowed = GovernedToolBridge(gateway, ExecutionPrincipal("alice", frozenset({"lookup_order"})))
    denied = GovernedToolBridge(gateway, ExecutionPrincipal("mallory", frozenset()))
    return recorder, audit, allowed, denied


def _definition():
    return ToolDefinition("lookup_order", "Look up one synthetic order", {"type": "object"})


@pytest.mark.asyncio
async def test_custom_registry_denies_without_invoking_handler(fixture):
    rec, audit, _allowed, denied = fixture
    registry = ToolRegistry([denied.local_provider([_definition()])])
    await registry.boot()
    with pytest.raises(PermissionError):
        await registry.call("lookup_order", {"order_id": "SO-1001"})
    assert rec.calls == 0
    assert audit[-1]["event"] == "tool_blocked_or_failed"


@pytest.mark.asyncio
async def test_custom_registry_allows_one_call(fixture):
    rec, audit, allowed, _denied = fixture
    registry = ToolRegistry([allowed.local_provider([_definition()])])
    await registry.boot()
    result = await registry.call("lookup_order", {"order_id": "SO-1001"})
    assert result.ok and result.data == {"record": "SO-1001"}
    assert rec.calls == 1
    assert audit[-1]["event"] == "tool_completed"


@pytest.mark.asyncio
async def test_langchain_callback_path_denied(fixture):
    """Exercises the async callback without claiming SDK-agent orchestration."""
    rec, audit, _allowed, denied = fixture
    async def callback(order_id: str):
        return await denied.invoke("lookup_order", {"order_id": order_id})
    with pytest.raises(PermissionError):
        await callback(order_id="SO-1001")
    assert rec.calls == 0
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_openai_agents_callback_path_denied(fixture):
    rec, audit, _allowed, denied = fixture
    async def callback(_ctx, params):
        return await denied.invoke("lookup_order", json.loads(params))
    with pytest.raises(PermissionError):
        await callback(None, '{"order_id":"SO-1001"}')
    assert rec.calls == 0
    assert len(audit) == 1


@pytest.mark.asyncio
async def test_protected_action_denied_before_handler(fixture):
    rec, audit, _, _ = fixture
    gateway = ExecutionGateway({"lookup_order": rec.handle}, audit=audit.append,
                               protected_tools=frozenset({"lookup_order"}))
    bridge = GovernedToolBridge(gateway, ExecutionPrincipal("alice", frozenset({"lookup_order"})))
    with pytest.raises(PermissionError, match="approval"):
        await bridge.invoke("lookup_order", {"order_id": "SO-1001"})
    assert rec.calls == 0
    assert audit[-1]["event"] == "tool_blocked_or_failed"


@pytest.mark.asyncio
async def test_unregistered_tool_denied_before_handler(fixture):
    rec, audit, _, denied = fixture
    with pytest.raises(PermissionError):
        await denied.invoke("unregistered", {"order_id": "SO-1001"})
    assert rec.calls == 0
    assert audit[-1]["event"] == "tool_blocked_or_failed"


def test_blank_principal_fails_closed(fixture):
    _rec, _audit, allowed, _denied = fixture
    with pytest.raises(ValueError):
        GovernedToolBridge(allowed._gateway, ExecutionPrincipal("", frozenset()))


@pytest.mark.asyncio
async def test_invalid_arguments_not_dispatched(fixture):
    rec, _audit, allowed, _denied = fixture
    with pytest.raises(TypeError):
        await allowed.invoke("lookup_order", ["SO-1001"])
    assert rec.calls == 0

@pytest.mark.asyncio
async def test_langchain_sdk_wrapper_delegates_to_gateway(fixture, monkeypatch):
    import sys
    import types
    rec, audit, _allowed, denied = fixture

    class FakeStructuredTool:
        @staticmethod
        def from_function(*, coroutine, name, description, args_schema):
            return types.SimpleNamespace(ainvoke=coroutine, name=name)

    fake_parent = types.ModuleType("langchain_core")
    fake_tools = types.ModuleType("langchain_core.tools")
    fake_tools.StructuredTool = FakeStructuredTool
    monkeypatch.setitem(sys.modules, "langchain_core", fake_parent)
    monkeypatch.setitem(sys.modules, "langchain_core.tools", fake_tools)
    tool = denied.langchain_tool("lookup_order", description="lookup", args_schema=dict)
    with pytest.raises(PermissionError):
        await tool.ainvoke(order_id="SO-1001")
    assert rec.calls == 0 and audit[-1]["event"] == "tool_blocked_or_failed"


@pytest.mark.asyncio
async def test_openai_sdk_wrapper_delegates_to_gateway(fixture, monkeypatch):
    import sys
    import types
    rec, audit, _allowed, denied = fixture

    class FakeFunctionTool:
        def __init__(self, **kwargs):
            self.on_invoke_tool = kwargs["on_invoke_tool"]

    fake_agents = types.ModuleType("agents")
    fake_agents.FunctionTool = FakeFunctionTool
    monkeypatch.setitem(sys.modules, "agents", fake_agents)
    tool = denied.openai_agents_tool("lookup_order", description="lookup", schema={"type":"object"})
    with pytest.raises(PermissionError):
        await tool.on_invoke_tool(None, '{"order_id": "SO-1001"}')
    assert rec.calls == 0 and audit[-1]["event"] == "tool_blocked_or_failed"


@pytest.mark.asyncio
async def test_openai_wrapper_rejects_non_object_json(fixture, monkeypatch):
    import sys
    import types
    rec, _audit, allowed, _denied = fixture
    class FakeFunctionTool:
        def __init__(self, **kwargs):
            self.on_invoke_tool = kwargs["on_invoke_tool"]
    fake_agents = types.ModuleType("agents")
    fake_agents.FunctionTool = FakeFunctionTool
    monkeypatch.setitem(sys.modules, "agents", fake_agents)
    tool = allowed.openai_agents_tool("lookup_order", description="lookup", schema={"type":"object"})
    with pytest.raises(ValueError):
        await tool.on_invoke_tool(None, '["SO-1001"]')
    assert rec.calls == 0
