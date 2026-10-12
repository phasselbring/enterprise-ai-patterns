# Changelog

## 0.3.0 — governance and security hardening

Fixes defects where the governance guarantees described in the README did not hold under failure
or adversarial input. `tests/regression/test_review_defects.py` has one test per defect; it uses
only pre-0.3.0 interfaces, so it fails against 0.2.0 and passes against 0.3.0.

### Breaking changes

Existing public names, signatures and exception base classes are preserved. New parameters are
keyword-only with defaults. The following *behaviour* changes may affect callers:

**Text-to-SQL (`text_to_sql/safe_text_to_sql.py`)**
- Requires `sqlglot>=26`, via the new `sql` extra (`pip install -e ".[sql]"`; also in `dev`/`all`).
- Previously accepted queries are now rejected: comma joins and quoted references to tables outside
  the allowlist, schema- or database-qualified tables not on the allowlist, functions outside an
  allowlist (`pg_read_file`, `pg_sleep`, `dblink`, …), table-valued functions, `SELECT ... INTO`,
  `FOR UPDATE/SHARE`, and data-modifying CTEs (`WITH x AS (DELETE ... RETURNING *) SELECT ...`).
- Previously rejected queries are now accepted: `WITH` (CTE) queries, `SELECT` followed by a newline,
  string literals containing keywords such as `'update pending'`, and a trailing comment after `;`.
- `validate_read_only_sql` now also enforces the function allowlist; `validate_table_allowlist` now
  parses the statement and fails on unparseable SQL.
- New: `validate_query(sql, *, allowed_tables, allowed_functions, dialect)` runs both checks;
  `ALLOWED_TABLES` is now a `frozenset`.

**Agent loop (`agents/loop.py`)**
- A denied tool, unknown tool, malformed tool decision, executor error or failed verification no
  longer raises out of `run()`. Each is recorded as a `tool_error` event (`denied`, `unknown_tool`,
  `malformed_decision`, `execution_failed`, `verification_failed`) that the model sees on its next
  turn. Callers that caught `PermissionError("denied")` or `RuntimeError("verification failed")`
  from `run()` will no longer see them.
- Approval-required still raises (`ApprovalRequired`, a `PermissionError`), but first saves an
  `awaiting_approval` event. Call `run` again with the same session once approved.
- Resuming a session now raises `PermissionError` for a different `caller_id`,
  `SessionCompletedError` (a `ValueError`) for a completed session, and `ValueError` for a
  different goal.
- `max_steps` is now a lifetime budget per session, across all `run` calls, instead of per call.
  Exhaustion raises `StepBudgetExceeded`, a `RuntimeError` subclass as before. `max_steps <= 0`
  is rejected at construction.
- `RegistryExecutor` now replays the stored result when an idempotency key repeats. New optional
  `idempotency_store` parameter on `AgentLoop` and `store` on `RegistryExecutor`.

**Governed tool calls (`agents/governed_tool_call.py`)**
- Idempotency keys change value: they are derived from caller, tool and arguments, no longer from
  `trace_id`. Keys persisted by 0.2.0 will not match.
- New optional `ToolRequest.idempotency_key` field (defaults to `None`, excluded from equality).
- Failures raise subclasses of the previous exceptions: `ToolDenied` / `ApprovalRequired`
  (`PermissionError`), `ToolExecutionError` / `ToolVerificationError` (`RuntimeError`). Executor
  exceptions are wrapped in `ToolExecutionError`, with the original as `__cause__`.
- The async path no longer calls `verify` when the result is not `ok` (matching the sync path).
- Audit events gain `caller_id`, `tool_name` and `idempotency_key` fields, and two new events:
  `tool_failed`, and `tool_verification_failed` with `error_type` when the verifier raises.

**Tool providers**
- `operation_id` now has a per-call suffix: `local:{tool}:{uuid}` and `mcp:{tool}:{uuid}`, instead
  of the constant `local:{tool}` / `mcp:{tool}`.

**RAG context assembly (`rag/post_retrieval.py`)**
- `ContextBuilder` skips a chunk that does not fit instead of stopping, and counts the separators
  between chunks against `max_chars`, so `rendered` never exceeds the budget. Selections near the
  budget may differ by a chunk.

### Other
- CI runs on Python 3.11, 3.12 and 3.13.
- `docs/agent_harness.md` documents the loop's failure handling and session rules.
