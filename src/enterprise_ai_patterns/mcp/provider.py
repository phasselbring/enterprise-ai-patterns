from __future__ import annotations

from typing import Any
import uuid

from enterprise_ai_patterns.agents.tool_registry import (
    ToolCallResult,
    ToolDefinition,
)


class MCPToolProvider:
    """Adapts a remote MCP server to the generic agent ToolProvider interface.

    The import is lazy so the core package/test suite does not require the MCP optional extra.
    For a high-throughput production client, keep a connection/pool alive rather than opening a
    connection for every call as this compact reference does.
    """

    def __init__(self, server_url: str) -> None:
        self._server_url = server_url

    @staticmethod
    def _client_class():
        try:
            from mcp import Client
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError('Install the "mcp" extra: pip install -e ".[mcp]"') from exc
        return Client

    async def list_tools(self) -> list[ToolDefinition]:
        Client = self._client_class()
        async with Client(self._server_url) as client:
            result = await client.list_tools()
            return [
                ToolDefinition(
                    name=tool.name,
                    description=tool.description or tool.title or tool.name,
                    input_schema=tool.input_schema,
                    source=f"mcp:{self._server_url}",
                )
                for tool in result.tools
            ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        Client = self._client_class()
        async with Client(self._server_url) as client:
            result = await client.call_tool(name, arguments)
            data = result.structured_content
            if data is None:
                data = {
                    "content": [getattr(block, "text", str(block)) for block in result.content]
                }
            elif not isinstance(data, dict):
                data = {"structured_content": data}
            return ToolCallResult(
                ok=not result.is_error,
                data=data,
                operation_id=f"mcp:{name}:{uuid.uuid4()}",
            )
