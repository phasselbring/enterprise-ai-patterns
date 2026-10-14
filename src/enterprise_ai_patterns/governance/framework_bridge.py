"""Framework bridges that make all tool calls cross the same execution gateway.

The application constructs these objects with a server-authenticated principal.
The LLM may supply *arguments*, but may not supply its own principal, tool
permissions, action ID, or approval decision. This is example glue, not an
identity provider, and not an exactly-once transaction coordinator.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import uuid4

from .authorization import ExecutionPrincipal
from .execution_gateway import ExecutionGateway


class GovernedToolBridge:
    """Single trusted tool entry point, shared by all adapter wrappers."""

    def __init__(self, gateway: ExecutionGateway, principal: ExecutionPrincipal):
        if not principal.caller_id:
            raise ValueError("authenticated principal required")
        self._gateway = gateway
        self._principal = principal

    async def invoke(self, tool_name: str, arguments: dict[str, Any], *, resource_id: str = "") -> Any:
        if not isinstance(arguments, dict):
            raise TypeError("tool arguments must be a dictionary")
        # Generate action IDs outside the LLM. A real sensitive-write workflow
        # must bind IDs and approvals to a server-generated action record.
        return await self._gateway.execute(
            self._principal, tool_name, arguments,
            action_id=uuid4().hex, resource_id=resource_id,
        )

    def local_provider(self, definitions):
        """Wrap ToolDefinition objects for the existing ToolRegistry.

        A caller MUST register only these wrapped handlers (never register a
        direct handler under the same tool name in a separate provider).
        """
        from enterprise_ai_patterns.agents.tool_registry import LocalToolProvider

        provider = LocalToolProvider()
        for definition in definitions:
            async def handler(arguments, *, _name=definition.name):
                return await self.invoke(_name, arguments)
            provider.register(definition, handler)
        return provider

    def langchain_tool(self, name: str, *, description: str, args_schema: type):
        """Create a real LangChain StructuredTool, if installed.

        Only this wrapper should be passed to create_agent(); exposing the
        raw backend alongside it would bypass this gateway.
        """
        try:
            from langchain_core.tools import StructuredTool
        except ImportError as exc:
            raise RuntimeError("install langchain-core for this adapter") from exc

        async def invoke(**kwargs):
            return await self.invoke(name, kwargs)

        return StructuredTool.from_function(
            coroutine=invoke, name=name, description=description,
            args_schema=args_schema,
        )

    def openai_agents_tool(self, name: str, *, description: str,
                          schema: dict[str, Any]):
        """Create an OpenAI Agents SDK FunctionTool, if installed.

        The SDK invokes this callback with JSON input; we parse only arguments
        and never trust identity, approval, or authorization from that input.
        """
        try:
            import json
            from agents import FunctionTool
        except ImportError as exc:
            raise RuntimeError("install openai-agents for this adapter") from exc

        async def on_invoke_tool(_context, params: str):
            args = json.loads(params)
            if not isinstance(args, dict):
                raise ValueError("tool arguments must be an object")
            return await self.invoke(name, args)

        return FunctionTool(
            name=name, description=description,
            params_json_schema=schema, on_invoke_tool=on_invoke_tool,
            strict_json_schema=False,
        )
