# Harness validation methodology

## Layers

- **Contract tests**: identical request/result schemas for every harness, offline.
- **Deterministic scenario tests**: frozen synthetic business data, correct results and fail-closed responses.
- **Security gates**: unauthorized data access, forbidden tool execution, missing approvals, prompt injection and cross-user resume must produce no side effect. Failing any gate fails the run irrespective of task accuracy.
- **Fault injection**: tool errors, timeouts, malformed data, audit outages and retries.
- **Provider matrix**: repeat runs with identical scenarios across models and harnesses; record model version, costs and p50/p95 latency separately from accuracy.

## Current limitations

The offline comparison is a scaffold, not a live multi-harness benchmark. The basic scorecard checks only completion, expected text and explicitly forbidden tool calls; it cannot prove that hidden tool execution, data leakage or duplicate writes did not occur. Those checks require independent mock service counters, auditable backend records and end-to-end adversarial testing. Protect raw traces and report versions and sample sizes before claiming reliability.
