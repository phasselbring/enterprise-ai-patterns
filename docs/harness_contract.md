# Agent harness contract

The common `HarnessRequest` identifies a task, session, authenticated caller, prompt, permitted tools and step budget. `HarnessResult` supplies normalized status, answer, tool summaries, audit evidence, timing and error category. `AgentHarness.run()` is asynchronous.

## Implementations

- `CustomAgentLoopAdapter`: forwards caller/session/goal to the existing custom `AgentLoop`; the underlying loop retains security and step-budget controls.
- `LangChainHarnessAdapter`: wraps a supplied LangChain runnable. It **does not** govern every tool call; integrate `ExecutionGateway` with framework middleware and independent backend controls before deploying.
- `OpenAIAgentsAdapter`: accepts an injected SDK runner and agent. SDK installation and restricted tool wiring are deliberately optional.

A harness request does not authenticate a person: the API or trusted invocation layer must construct it from verified credentials. Caller-selected tool allowlists are never an authorization source. Never treat framework-specific errors as permission grants.
