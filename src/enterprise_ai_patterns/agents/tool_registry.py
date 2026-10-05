from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    source: str = "local"


@dataclass(frozen=True)
class ToolCallResult:
    ok: bool
    data: dict[str, Any]
    operation_id: str


class ToolProvider(Protocol):
    async def list_tools(self) -> list[ToolDefinition]: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult: ...


class LocalToolProvider:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None:
        if definition.name in self._definitions:
            raise ValueError(f"duplicate tool: {definition.name}")
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    async def list_tools(self) -> list[ToolDefinition]:
        return list(self._definitions.values())

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        handler = self._handlers.get(name)
        if handler is None:
            return ToolCallResult(False, {"error": "unknown tool"}, f"local:{name}:missing")
        data = await handler(arguments)
        return ToolCallResult(True, data, f"local:{name}")


class ToolRegistry:
    """Discovers tools from one or more providers (local APIs, MCP servers, etc.)."""

    def __init__(self, providers: list[ToolProvider]) -> None:
        self._providers = providers
        self._definitions: dict[str, ToolDefinition] = {}
        self._owners: dict[str, ToolProvider] = {}
        self._booted = False

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._definitions.values())

    async def boot(self) -> None:
        definitions: dict[str, ToolDefinition] = {}
        owners: dict[str, ToolProvider] = {}
        for provider in self._providers:
            for tool in await provider.list_tools():
                if tool.name in definitions:
                    raise ValueError(f"duplicate discovered tool: {tool.name}")
                definitions[tool.name] = tool
                owners[tool.name] = provider
        self._definitions = definitions
        self._owners = owners
        self._booted = True

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        if not self._booted:
            raise RuntimeError("tool registry must be booted before use")
        provider = self._owners.get(name)
        if provider is None:
            return ToolCallResult(False, {"error": "unknown tool"}, f"registry:{name}:missing")
        return await provider.call_tool(name, arguments)
