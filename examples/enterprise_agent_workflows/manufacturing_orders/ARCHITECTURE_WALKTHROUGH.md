# Architecture walkthrough

1. **User request:** Investigate synthetic order SO-1001.
2. **Model selection (`model_config.py`):** Choose OpenAI, Claude, or Gemini through environment configuration. Credentials belong to the provider, not in source.
3. **Agent (`agent_runner.py`):** LangChain selects tools and stores the conversation. It does not have unconditional transaction authority.
4. **MCP (`mcp_server.py`):** The standard tool interface exposes order lookup, shortage calculation, and customer draft. The server starts through stdio. No send tool is offered.
5. **Domain (`domain.py`):** Arithmetic and approval requirements are deterministic. The model is not trusted to invent quantities or grant its own approvals.
6. **Comparison (`compare_models.py`):** Identical synthetic tasks go to each provider. Per-call traces and seven smoke checks are recorded; runs are not statistically meaningful model rankings.
7. **Approval (`approval_workflow.py`):** LangGraph demonstrates an interrupt and a denied resume. No real escalation occurs; production requires durable checkpoints and identity-bound external approvals.

## Security boundaries

- Treat all MCP results and retrieved documents as **untrusted data**, not authority. XML-style wrappers are explanatory only; prompt-injection resistance requires further testing and downstream authorization.
- Validate caller identity and ACL on the server side **before** retrieval top-k, plus defense-in-depth checks after retrieval.
- A database idempotency result cache survives restarts, but it **does not** provide atomic exactly-once execution for concurrent writers. The actual transaction service needs durable claim/lease and downstream idempotency.
- An LLM should never be able to send a customer notice or modify inventory just because text instructs it to.
- Never expose API keys, traces, internal client data, or secrets in public reports.
