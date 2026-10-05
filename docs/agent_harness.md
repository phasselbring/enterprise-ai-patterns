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
