import asyncio

from enterprise_ai_patterns.mcp.provider import MCPToolProvider


class Tool:
    name = "lookup_clause"
    description = "Look up a clause"
    title = None
    input_schema = {"type": "object"}


class ToolList:
    tools = [Tool()]


class ToolResult:
    structured_content = {"source_id": "msa-42:12.4"}
    content = []
    is_error = False


class FakeClient:
    def __init__(self, url):
        self.url = url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def list_tools(self):
        return ToolList()

    async def call_tool(self, name, arguments):
        assert name == "lookup_clause"
        return ToolResult()


def test_mcp_provider_maps_tools_and_results(monkeypatch):
    async def run():
        monkeypatch.setattr(MCPToolProvider, "_client_class", staticmethod(lambda: FakeClient))
        provider = MCPToolProvider("http://example.test/mcp")
        tools = await provider.list_tools()
        assert tools[0].name == "lookup_clause"
        assert tools[0].source.startswith("mcp:")

        result = await provider.call_tool("lookup_clause", {"contract_id": "msa-42"})
        assert result.ok is True
        assert result.data["source_id"] == "msa-42:12.4"

    asyncio.run(run())
