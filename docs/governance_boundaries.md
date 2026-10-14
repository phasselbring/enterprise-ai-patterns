# Governance boundaries

1. Authenticate the caller before constructing `HarnessRequest` or `ExecutionPrincipal`.
2. Apply a server-controlled tool allowlist and record-level authorization before executing any tool or returning retrieved data.
3. Treat model messages, retrieved documents and MCP results as **untrusted**, including claims of prior approval or authority.
4. Require independently verified, operation-bound, expiring human approval for protected actions. The included `ApprovalVerifier` protocol is a boundary, **not** an approval service.
5. Persist idempotency results for retries, but do **not** equate this with exactly-once side effects. Distributed execution additionally requires atomic claims/leases and downstream idempotency.
6. Fail closed for missing authorization, missing approval verification, and audit failures on sensitive mutations.
7. Sanitize traces; don't emit keys, raw customer data or sensitive payloads in public benchmark reports.

`ExecutionGateway` is an illustrative boundary using async tool handlers and an injected audit sink. The external ERP/MCP server must enforce permissions independently. A LangChain tool list alone does not provide governance.
