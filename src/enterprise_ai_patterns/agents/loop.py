from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol
import uuid

from .governed_tool_call import ToolRequest, ToolResult, governed_execute_async
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


class RegistryExecutor:
    def __init__(self, registry: ToolRegistry, verifier) -> None:
        self._registry = registry
        self._verifier = verifier

    async def execute(self, request: ToolRequest, *, idempotency_key: str) -> ToolResult:
        result = await self._registry.call(request.tool_name, request.arguments)
        return ToolResult(result.ok, result.data, result.operation_id)

    async def verify(self, result: ToolResult) -> bool:
        return await self._verifier.verify(result)


class AgentLoop:
    """Bounded model-driven control loop with explicit state and governed tool use."""

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
    ) -> None:
        self._model = model
        self._context_loader = context_loader
        self._registry = tool_registry
        self._state_store = state_store
        self._policy = policy
        self._approvals = approvals
        self._executor = RegistryExecutor(tool_registry, verifier)
        self._audit = audit
        self._max_steps = max_steps

    async def run(self, *, session_id: str, caller_id: str, goal: str) -> str:
        await self._registry.boot()
        state = self._state_store.load(session_id)
        if state is None:
            state = AgentState(
                session_id=session_id,
                caller_id=caller_id,
                goal=goal,
                boot_context=await self._context_loader.load(caller_id=caller_id, goal=goal),
            )
            self._state_store.save(state)

        for _ in range(self._max_steps):
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
                raise ValueError("tool decision requires tool_name")

            request = ToolRequest(
                caller_id=caller_id,
                tool_name=decision.tool_name,
                arguments=decision.arguments,
                trace_id=str(uuid.uuid4()),
            )
            result = await governed_execute_async(
                request,
                policy=self._policy,
                approvals=self._approvals,
                executor=self._executor,
                audit=self._audit,
            )
            state.append(
                "tool_result",
                tool=decision.tool_name,
                arguments=decision.arguments,
                result=result.data,
                operation_id=result.operation_id,
            )
            self._state_store.save(state)

        state.append("max_steps_exceeded")
        self._state_store.save(state)
        raise RuntimeError("agent exceeded max_steps without a final answer")
