# Query planning and retrieval routing

`BasicQueryPlanner` intentionally does **only** whitespace normalization,
callback-based intent classification, query expansion and deduplication. It does
not perform semantic rewriting, decomposition, source selection, or populate
metadata filters on its own.

`RuleBasedQueryPlanner` is an **optional, deterministic, limited-vocabulary**
example. It recognizes explicit order, inventory, and escalation-policy terms,
extracts `region=FL` and `order_status=open` when explicitly present, and
produces multiple retrieval queries. `routed_queries()` maps known templates to
logical sources (`erp_orders`, `inventory`, `policy_documents`). This is neither
an open-domain language interpreter nor an LLM planner.

`RetrievalRouter` dispatches only to adapters configured by the host application.
A backend receives `caller` and `metadata_filters` and **must** apply both
its authorization predicate and the metadata predicate *inside* the search
backend, before ranking and top-k. Routing is not an authorization decision.
Unrecognized backend names fail closed. Production code must derive `caller`
from verified identity, not model output.

The default `ProductionRAGPipeline` remains backwards compatible and calls its
existing caller-aware retriever. To use explicit source routing, inject both a
`RuleBasedQueryPlanner` and a `RetrievalRouter` into the pipeline's optional
`router=` argument; configured adapters must implement
`search(query, *, limit, caller, metadata_filters)`. For actual ERP/SQL data
and APIs, use governed business tools rather than suggesting documents alone
can implement transactions.

## PowerShell validation

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_query_planning_routing.py -v
.\.venv\Scripts\python.exe -m pytest -q
```

## Gaps and tradeoffs

- No LLM-assisted planning, entity resolution beyond explicit vocabulary, or
  confidence calibrated intent classifier.
- No dynamic selection of arbitrary tool or MCP services.
- Routing does not authenticate users or enforce downstream ACLs by itself.
- Filters are illustrative business metadata, never tenant or entitlement claims.
- New domains require explicitly reviewed rules, adapters, and golden tests.
