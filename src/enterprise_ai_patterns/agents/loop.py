from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Protocol
import uuid

from .governed_tool_call import (
    ApprovalRequired,
    ToolDenied,
    ToolExecutionError,
    ToolRequest,
    ToolResult,
    ToolVerificationError,
    governed_execute_async,
    idempotency_key,
)
from .state import AgentState, StateStore
from .tool_registry import ToolRegistry


class DecisionKind(str, Enum):
    TOOL = "tool"
    FINAL = "final"
    ABSTAIN = "abstain"


@dataclass(frozen=True)
class AgentDecision:
    kind: DecisionKind
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    answer: str | None = None


@dataclass(frozen=True)
class AgentTurn:
    goal: str
    boot_context: dict[str, Any]
    tool_definitions: tuple[Any, ...]
    prior_events: tuple[Any, ...]


class AgentModel(Protocol):
    async def decide(self, turn: AgentTurn) -> AgentDecision: ...


class BootContextLoader(Protocol):
    async def load(self, *, caller_id: str, goal: str) -> dict[str, Any]: ...


class SessionCompletedError(ValueError):
    """The session already reached a final answer or abstained; start a new session instead."""


class StepBudgetExceeded(RuntimeError):
    """The session used its whole step budget without a final answer."""


class IdempotencyStore(Protocol):
    def get(self, key: str) -> ToolResult | None: ...
    def put(self, key: str, result: ToolResult) -> None: ...


class InMemoryIdempotencyStore:
    """Process-local store. Production needs a durable store shared by all workers."""

    def __init__(self) -> None:
        self._results: dict[str, ToolResult] = {}

    def get(self, key: str) -> ToolResult | None:
        return self._results.get(key)

    def put(self, key: str, result: ToolResult) -> None:
        self._results[key] = result


class RegistryExecutor:
    """Executes registry tools, replaying the stored result when an idempotency key repeats."""

    def __init__(self, registry: ToolRegistry, verifier, store: IdempotencyStore | None = None) -> None:
        self._registry = registry
        self._verifier = verifier
        self._store = store or InMemoryIdempotencyStore()

    async def execute(self, request: ToolRequest, *, idempotency_key: str) -> ToolResult:
        previous = self._store.get(idempotency_key)
        if previous is not None:
            return previous
        result = await self._registry.call(request.tool_name, request.arguments)
        tool_result = ToolResult(result.ok, result.data, result.operation_id)
        if tool_result.ok:
            self._store.put(idempotency_key, tool_result)
        return tool_result

    async def verify(self, result: ToolResult) -> bool:
        return await self._verifier.verify(result)


_TOOL_ERRORS: tuple[tuple[type[Exception], str], ...] = (
    (ToolDenied, "denied"),
    (ToolExecutionError, "execution_failed"),
    (ToolVerificationError, "verification_failed"),
)


class AgentLoop:
    """Bounded model-driven control loop with explicit state and governed tool use.

    * Tool denials, unknown tools, malformed decisions and tool failures are recorded as
      ``tool_error`` events and shown to the model on its next turn, so it can recover or abstain.
    * A call that needs approval pauses the session (``awaiting_approval`` event) and raises
      :class:`ApprovalRequired`; call ``run`` again with the same session once it is approved.
    * A session belongs to the caller that created it, cannot be re-run once completed, and has
      one step budget (``max_steps``) for its whole life, across every ``run`` call.
    """

    def __init__(
        self,
        *,
        model: AgentModel,
        context_loader: BootContextLoader,
        tool_registry: ToolRegistry,
        state_store: StateStore,
        policy,
        approvals,
        verifier,
        audit,
        max_steps: int = 8,
        idempotency_store: IdempotencyStore | None = None,
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
        self._model = model
        self._context_loader = context_loader
        self._registry = tool_registry
        self._state_store = state_store
        self._policy = policy
        self._approvals = approvals
        self._executor = RegistryExecutor(tool_registry, verifier, idempotency_store)
        self._audit = audit
        self._max_steps = max_steps

    async def _open_session(self, *, session_id: str, caller_id: str, goal: str) -> AgentState:
        state = self._state_store.load(session_id)
        if state is None:
            state = AgentState(
                session_id=session_id,
                caller_id=caller_id,
                goal=goal,
                boot_context=await self._context_loader.load(caller_id=caller_id, goal=goal),
            )
            self._state_store.save(state)
            return state

        if state.caller_id != caller_id:
            self._audit.append({
                "event": "session_access_denied",
                "session_id": session_id,
                "caller_id": caller_id,
            })
            raise PermissionError("session belongs to another caller")
        if state.completed:
            raise SessionCompletedError(f"session {session_id} is already completed")
        if state.goal != goal:
            raise ValueError("goal does not match the existing session; start a new session")
        return state

    def _record_tool_error(self, state: AgentState, decision: AgentDecision, error: str) -> None:
        state.append("tool_error", tool=decision.tool_name, arguments=decision.arguments, error=error)
        self._state_store.save(state)

    async def run(self, *, session_id: str, caller_id: str, goal: str) -> str:
        await self._registry.boot()
        state = await self._open_session(session_id=session_id, caller_id=caller_id, goal=goal)
        known_tools = {definition.name for definition in self._registry.definitions}

        while state.step_count < self._max_steps:
            decision = await self._model.decide(
                AgentTurn(
                    goal=state.goal,
                    boot_context=state.boot_context,
                    tool_definitions=self._registry.definitions,
                    prior_events=tuple(state.events),
                )
            )

            if decision.kind is DecisionKind.FINAL:
                state.append("final", answer=decision.answer or "")
                state.completed = True
                self._state_store.save(state)
                return decision.answer or ""

            if decision.kind is DecisionKind.ABSTAIN:
                state.append("abstain", answer=decision.answer or "insufficient evidence")
                state.completed = True
                self._state_store.save(state)
                return decision.answer or "insufficient evidence"

            if decision.kind is not DecisionKind.TOOL or not decision.tool_name:
                self._record_tool_error(state, decision, "malformed_decision")
                continue

            if decision.tool_name not in known_tools:
                self._record_tool_error(state, decision, "unknown_tool")
                continue

            request = ToolRequest(
                caller_id=caller_id,
                tool_name=decision.tool_name,
                arguments=decision.arguments,
                trace_id=str(uuid.uuid4()),
            )
            # Scope the key to this session step, so a retried step dedupes but a deliberate
            # repeat of the same call at a later step runs again.
            request = replace(
                request,
                idempotency_key=f"{session_id}:{state.step_count}:{idempotency_key(request)}",
            )

            try:
                result = await governed_execute_async(
                    request,
                    policy=self._policy,
                    approvals=self._approvals,
                    executor=self._executor,
                    audit=self._audit,
                )
            except ApprovalRequired:
                state.append("awaiting_approval", tool=decision.tool_name, arguments=decision.arguments)
                self._state_store.save(state)
                raise
            except (ToolDenied, ToolExecutionError, ToolVerificationError) as exc:
                code = next(name for kind, name in _TOOL_ERRORS if isinstance(exc, kind))
                self._record_tool_error(state, decision, code)
                continue

            state.append(
                "tool_result",
                tool=decision.tool_name,
                arguments=decision.arguments,
                result=result.data,
                operation_id=result.operation_id,
            )
            self._state_store.save(state)

        if not state.events or state.events[-1].kind != "max_steps_exceeded":
            state.append("max_steps_exceeded")
            self._state_store.save(state)
        raise StepBudgetExceeded("agent exceeded max_steps without a final answer")
