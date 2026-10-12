# Agent application harness

An agent is a bounded model-driven control loop, not simply an LLM call.

The reference flow is:

1. **Boot context** — load domain instructions, caller scope, task context, and other stable context.
2. **Tool discovery** — build an approved registry from local providers and/or MCP servers.
3. **State load** — recover explicit session/task state.
4. **Decide** — the model chooses `tool`, `final`, or `abstain`.
5. **Govern** — policy, approval, idempotency, execution-time authorization.
6. **Execute** — invoke the selected tool.
7. **Verify** — independently verify consequential results where possible.
8. **Observe + persist** — add the result to state and iterate.
9. **Stop** — final answer, abstention, or bounded max-step failure.

`agents/loop.py` composes these parts. Events store externalized decisions/actions/results, not hidden
model chain-of-thought.

## Failure handling and session rules

| Situation | What the loop does |
|---|---|
| Policy denies a tool | Records a `tool_error` event (`denied`); the model sees it next turn and can recover or abstain. |
| Unknown tool or malformed decision | Records `tool_error` (`unknown_tool` / `malformed_decision`); the tool never runs. |
| Tool raises, or verification fails | The governed call audits `tool_failed` / `tool_verification_failed`; the loop records `tool_error`. |
| Approval required | Records `awaiting_approval`, saves state and raises `ApprovalRequired`. Call `run` again with the same session once approved. |
| Different caller resumes a session | Audits `session_access_denied` and raises `PermissionError`. The model is never called. |
| Completed session is run again | Raises `SessionCompletedError`. Start a new session. |
| Step budget used up | `max_steps` covers the session's whole life, across every `run` call. Raises `StepBudgetExceeded`. |

Every tool call carries an idempotency key scoped to `session_id` and step number, so retrying a
step does not repeat its side effect, while a deliberate repeat at a later step does run.
`RegistryExecutor` replays the stored result for a repeated key; the default store is in-memory,
so production needs a durable store shared by every worker.
