# Enterprise AI Patterns

Implementation-oriented reference examples for production enterprise AI systems.

This repository intentionally separates the **public engineering patterns** from any proprietary
APEX implementation. It uses synthetic data and contains no client data, credentials, internal
endpoints, or production authorization rules.

## What this repository demonstrates

### Production RAG

```text
INGESTION / INDEXING
parse -> structure -> chunk -> metadata/ACL -> lexical + vector indexes

QUERY TIME
query
  -> pre-retrieval planning / rewrite / routing
  -> hybrid retrieval (lexical + dense)
  -> rank fusion
  -> authorization / metadata filtering
  -> reranking
  -> deduplication + context assembly
  -> generation
  -> citation + grounding verification
  -> trace + evaluation
```

Relevant code:

- `rag/pre_retrieval.py` — query normalization, decomposition/routing hooks
- `rag/hybrid_search.py` — reciprocal-rank fusion
- `rag/retrieval.py` — first-stage hybrid retrieval
- `rag/reranker.py` — deterministic reranker plus optional cross-encoder adapter
- `rag/post_retrieval.py` — deduplication and context assembly
- `rag/grounding.py` — citation and claim/evidence verification
- `rag/production_pipeline.py` — composes the complete flow

### Agent application harness

```text
boot context
   -> discover tool registry
   -> load state
   -> model selects action
   -> policy / approval gate
   -> tool execution
   -> observe result
   -> update state
   -> repeat until final / abstain / max steps
```

Relevant code:

- `agents/state.py` — explicit session/task state
- `agents/tool_registry.py` — local or remote tool discovery/invocation
- `agents/governed_tool_call.py` — policy, approval, idempotency, verification, audit
- `agents/loop.py` — bounded model-driven control loop (failure handling and session rules: `docs/agent_harness.md`)

### MCP

The optional MCP examples use the current MCP Python SDK v2 surface:

- `mcp/provider.py` — adapts an MCP server to the agent tool registry
- `examples/mcp/legal_server.py` — synthetic legal tools exposed via MCP
- `examples/mcp/client.py` — list/call those tools

Install with:

```bash
python -m pip install -e ".[mcp]"
```

### Fine-tuning data

- `fine_tuning/dataset.py` — validates and writes chat-style supervised examples
- `examples/fine_tuning/legal_chat_dataset.py` — synthetic legal task examples
- `docs/fine_tuning.md` — when to fine-tune vs retrieve

### Evaluation

- `evaluation/metrics.py` — Precision@K, Recall@K, MRR, nDCG
- `evaluation/golden.py` — frozen golden-case evaluation
- unit tests and acceptance tests validate success and failure paths

## Run tests

```bash
python -m pip install -e ".[dev]"
pytest -v
pytest --cov=enterprise_ai_patterns --cov-report=term-missing
```

Optional reranker support:

```bash
python -m pip install -e ".[rerank]"
```

## Enterprise manufacturing agent

[Run the multi-provider MCP manufacturing example](examples/enterprise_agent_workflows/manufacturing_orders/README.md). It uses synthetic data and supports OpenAI, Claude, and Gemini. See the linked architecture walkthrough for security limitations.

**Security notes:** New reference retrieval adapters must honor caller ACLs **before** top-k. The SQLite idempotency result store provides persistence but is not an exactly-once side-effect executor. Model-consumed retrieval evidence remains untrusted.
