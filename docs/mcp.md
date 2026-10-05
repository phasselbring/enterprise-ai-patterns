# MCP integration

MCP standardizes how hosts discover and call external tools/resources/prompts. In this repo it is a
**tool transport/discovery boundary**, not the policy boundary.

The agent still applies enterprise controls before invoking an MCP tool:

```text
agent decision
  -> approved tool registry
  -> policy / entitlement check
  -> approval gate if consequential
  -> MCP client
  -> MCP server
  -> domain API / system of record
  -> independent verification
  -> audit
```

The optional examples target the MCP Python SDK v2 API (`MCPServer` and `Client`).
