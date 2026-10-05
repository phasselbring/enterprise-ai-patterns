import asyncio
import pytest
from enterprise_ai_patterns.agents.tool_registry import (
    LocalToolProvider, ToolDefinition, ToolRegistry
)


def test_tool_registry_discovers_and_calls_local_tool():
    async def run():
        provider = LocalToolProvider()
        async def handler(args): return {"value": args["x"] + 1}
        provider.register(
            ToolDefinition("increment", "Increment x", {"type": "object"}),
            handler,
        )
        registry = ToolRegistry([provider])
        await registry.boot()
        assert [t.name for t in registry.definitions] == ["increment"]
        result = await registry.call("increment", {"x": 3})
        assert result.ok and result.data["value"] == 4
    asyncio.run(run())
