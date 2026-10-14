# Governed framework bridge (incremental integration)

`governance/framework_bridge.py` provides a single entry to `ExecutionGateway` and adapters for the repository's `ToolRegistry`, LangChain `StructuredTool`, and OpenAI Agents SDK `FunctionTool`.

## Trust boundary

The application supplies an authenticated `ExecutionPrincipal`. The language model supplies only tool arguments. All sensitive operations MUST enforce user/resource permissions and approval at the actual MCP server or destination system, not exclusively at the framework bridge. Do not expose raw backend tools alongside governed wrappers.

## Custom AgentLoop

Construct `bridge.local_provider([ToolDefinition(...)])`, then boot `ToolRegistry([provider])` and inject it into your custom `AgentLoop` setup. The definition name must match a registered `ExecutionGateway` handler. The handler delegates to `bridge.invoke`.

## LangChain

Construct `bridge.langchain_tool(name, description=..., args_schema=YourPydanticModel)`; pass the resulting `StructuredTool` to `create_agent`. This uses the SDK's asynchronous tool callback. This optional dependency is imported only when the method is invoked.

## OpenAI Agents SDK

Install `openai-agents` separately and construct `bridge.openai_agents_tool(name, description=..., schema={...})`. Supply the resulting `FunctionTool` to the SDK Agent; only model-supplied JSON tool arguments reach the bridge. Test SDK compatibility against the selected installed version before use.

## Validation limits

The offline tests exercise the real custom registry and model-framework callback equivalents without LLM calls. They do not prove complete LangChain/OpenAI SDK agent execution. The bridge does not yet provide atomic claim/lease idempotency, durable approvals, resource-level ACL checks, bounded retries, tool schema validation for custom registry operations, or a normalized end-to-end cross-framework scorecard. Unit tests for the optional SDK wrappers must be run after installing their dependencies. Do not characterize this reference bridge as production-secure.
