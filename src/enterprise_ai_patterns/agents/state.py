from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentEvent:
    kind: str
    data: dict[str, Any]


@dataclass
class AgentState:
    session_id: str
    caller_id: str
    goal: str
    boot_context: dict[str, Any] = field(default_factory=dict)
    events: list[AgentEvent] = field(default_factory=list)
    step_count: int = 0
    completed: bool = False

    def append(self, kind: str, **data: Any) -> None:
        self.events.append(AgentEvent(kind=kind, data=data))
        self.step_count += 1


class StateStore(Protocol):
    def load(self, session_id: str) -> AgentState | None: ...
    def save(self, state: AgentState) -> None: ...


class InMemoryStateStore:
    def __init__(self) -> None:
        self._states: dict[str, AgentState] = {}

    def load(self, session_id: str) -> AgentState | None:
        return self._states.get(session_id)

    def save(self, state: AgentState) -> None:
        self._states[state.session_id] = state
