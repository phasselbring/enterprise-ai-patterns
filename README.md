# Enterprise AI Patterns

Implementation-oriented reference examples for enterprise AI systems. These demonstrate architectural patterns and testable controls; they are **not** a production deployment or security certification.

This repository intentionally separates **public engineering patterns** from proprietary APEX implementations. The published examples use synthetic data and should contain no client data, credentials, internal endpoints, or production authorization rules.

## What this repository demonstrates

### RAG reference architecture

```text
INGESTION / INDEXING
parse -> structure -> chunk -> metadata/ACL -> lexical + vector indexes

QUERY TIME
query
  -> normalization, planning, bounded decomposition
  -> allowlisted source routing
  -> caller ACL + metadata prefiltering (inside each retrieval backend)
  -> hybrid retrieval (lexical + dense)
  -> rank fusion
  -> defense-in-depth authorization check
  -> reranking
  -> deduplication + context assembly
  -> generation
  -> citation / grounding verification
  -> tracing + evaluation
```

The source routing and metadata extraction are reference implementations for supported cases, not arbitrary natural-language routing. Production search backends must independently enforce access restrictions **before** top-k; post-retrieval checks are an additional safeguard, not a replacement.

Relevant code:

- `rag/pre_retrieval.py` — whitespace normalization and injectable hooks; optional `RuleBasedQueryPlanner` provides bounded manufacturing decomposition, intent labels, and metadata extraction
- `rag/routing.py` — allowlisted source routing that passes caller context and metadata to backend adapters
- `rag/hybrid_search.py` — reciprocal-rank fusion
- `rag/retrieval.py` — ACL-aware reference first-stage hybrid retrieval
- `rag/reranker.py` — deterministic reranker plus optional cross-encoder adapter
- `rag/post_retrieval.py` — deduplication and untrusted-evidence context assembly
- `rag/grounding.py` — citation and claim/evidence verification
- `rag/production_pipeline.py` — composes the reference flow
- `docs/query_planning.md` — planner/router scope and limitations

### Agent application harness

```text
boot context
   -> discover tool registry
   -> load state
   -> model selects action
   -> independent policy / approval gate
   -> tool execution
   -> observe result
   -> update state
   -> repeat until final / abstain / max steps
```

Relevant code:

- `agents/state.py` — explicit session/task state
- `agents/tool_registry.py` — local or remote tool discovery/invocation
- `agents/governed_tool_call.py` — policy, approval, idempotency, verification, audit
- `agents/sqlite_idempotency.py` — persistence of completed tool results; **not** atomic exactly-once side-effect execution across workers
- `agents/loop.py` — bounded model-driven loop, failure handling, session rules (`docs/agent_harness.md`)

### MCP and multi-provider agent example

The optional MCP examples expose synthetic tools through standardized tool interfaces:

- `mcp/provider.py` — adapts an MCP server to the agent tool registry
- `examples/mcp/legal_server.py` — synthetic legal tools
- `examples/mcp/client.py` — discovers and invokes those tools
- [`examples/enterprise_agent_workflows/manufacturing_orders/README.md`](examples/enterprise_agent_workflows/manufacturing_orders/README.md) — executable synthetic manufacturing order-exception agent

The manufacturing example uses **LangChain** to orchestrate tool selection, **MCP** to expose typed business tools, and selectable **OpenAI, Claude, and Gemini** model providers. A separate **LangGraph** example demonstrates interrupt/resume for an approval decision. Its approval action is simulated; an interrupt is not itself server-side authorization. Each provider passed seven scenario smoke checks in prior local runs; this is not a statistical quality or safety benchmark.

### Fine-tuning data

- `fine_tuning/dataset.py` — validates and writes chat-style supervised examples
- `examples/fine_tuning/legal_chat_dataset.py` — synthetic legal task examples
- `docs/fine_tuning.md` — when to fine-tune versus retrieve

### Evaluation

- `evaluation/metrics.py` — Precision@K, Recall@K, MRR, nDCG
- `evaluation/golden.py` — frozen golden-case evaluation
- Unit, acceptance and regression tests exercise success and failure paths

## Capability status

| Area | Implemented reference capability | Production extension / limitation |
|---|---|---|
| Query planning | Deterministic planning, supported rule-based decomposition and intent labels | General-purpose semantic or LLM planning |
| Source routing | Allowlisted reference router | Real ERP/SQL/vector adapters with independent backend authorization |
| Retrieval authorization | Caller-aware pre-top-k filtering in reference retrieval | Verified ACL enforcement within every production search backend |
| MCP agent | Synthetic order, inventory and customer-draft tools across three providers | Enterprise identity and real business APIs |
| Approval | LangGraph interrupt/resume simulation | Durable authenticated approval records and independent enforcement |
| Idempotency | Stable keys and optional persisted completed results | Atomic claim/lease, crash recovery and downstream idempotency |
| Evaluation | Golden cases, regression and smoke checks | Representative adversarial corpus and statistical reliability/cost evaluation |
| Prompt injection | Untrusted-evidence formatting | Adversarial evaluation and enforced action boundaries; formatting alone is insufficient |

## Install and test

From the repository root, with an activated Python 3.11+ virtual environment:

```powershell
python -m pip install -e ".[dev,sql,agent-workflows]"
python -m pytest -v
python -m pytest --cov=enterprise_ai_patterns --cov-report=term-missing
```

Optional reranker support:

```powershell
python -m pip install -e ".[rerank]"
```

For credential setup, running each model, and the LangGraph approval simulation, follow the [manufacturing example README](examples/enterprise_agent_workflows/manufacturing_orders/README.md). Never commit credentials, local `hidden/` files, or raw agent trace reports.

## Security boundaries

Real systems must enforce authenticated caller identity and resource-level authorization inside their tool and retrieval backends. LLM outputs and retrieved documents are untrusted inputs, not permission grants. The repository's synthetic examples and smoke tests do not establish production readiness.
