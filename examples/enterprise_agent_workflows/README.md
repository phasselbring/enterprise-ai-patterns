# Enterprise Sales-Order Exception Agent (interview reference)

A self-contained **synthetic** business example illustrating a workflow and MCP tools. No real ERP, e-mail or customer systems are connected. It is not production-secure and is not part of proprietary APEX.

## Architecture

User -> LangChain `create_agent` (LLM decides next tool) -> `MCPAdapter` (MCP client)
-> MCP server (stdio) -> allowlisted typed tools -> synthetic orders
-> model summarizes grounded tool results. Read-only by design; customer communications are drafts only.

`domain.py` models stock, exception evaluation, customer draft, and an illustrative server-side approval gate. **The escalation function is not registered as an MCP tool**. A caller passing `approved=True` directly is not secure; a production backend must independently authenticate identity and verify a tamper-resistant approval record.

## Windows PowerShell

```powershell
cd C:\path\to\interview_agent_example
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m unittest discover -v
.\.venv\Scripts\python.exe .\deterministic_demo.py
.\.venv\Scripts\python.exe -m pip install "mcp>=2,<3" "langchain[mcp]>=1.4.0" langchain-openai
$env:OPENAI_API_KEY = "<your-key>"
$env:AGENT_MODEL = "openai:gpt-4.1-mini"
.\.venv\Scripts\python.exe .\langchain_agent.py
```

You can separately start `mcp_server.py` but it will wait for protocol messages on stdio; normal operation launches it from the agent. The pinned dependency ranges are illustrative; verify compatibility with your environment.

## Interview walkthrough

1. Business question: why is order SO-1001 late?
2. `lookup_order` retrieves only the authorized order (real deployments MUST add identity/entitlement checks).
3. `check_inventory_shortage` calculates 30 demanded minus 8 available = **22 units**; 12-day replenishment estimate.
4. `propose_customer_update` generates a **draft**; never sends it.
5. Approval escalation is required; demo refuses unapproved mutation.
6. Tests cover shortage, in-stock, unknown order, draft-only communications, denied escalation.

## Production-hardening backlog

- Per-request identities and server-side ACL/policy on each tool and record
- OAuth/OIDC, least-privilege and scoped access, secret handling
- Approval service with durable approvals bound to user, resource, action, args, TTL
- Idempotency keys, retries/timeouts, error classes, compensating actions
- RAG retrieval with ACL filtering and cited sources for policy documents
- Persisted workflow state / human-in-the-loop via LangGraph checkpointer
- Structured responses, PII/DLP protections, budget/rate limiting
- OTel traces with secret redaction, token/cost/latency metrics
- Contract tests, injection adversarial tests and frozen regression datasets
- Production integrations for ERP and CRM instead of in-memory dictionaries

## Key framework distinction

**MCP is a standardized tool interface, not an agent brain**. LangChain builds the model/tool loop; LangGraph adds durable state, branches, checkpoints and interrupt/resume; an MCP server exposes typed operations; the gateway independently enforces security.

# Enterprise agent workflows — incremental update

This overlay adds multi-provider model comparison, model/tool-call tracing, a smoke-test evaluator, and a simulated human-approval LangGraph reference to the existing manufacturing-order demo.