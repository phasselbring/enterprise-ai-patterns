"""Framework-neutral harness contracts. Identity must originate from a trusted server."""
from dataclasses import dataclass, field
from typing import Any, Protocol

@dataclass(frozen=True)
class HarnessRequest:
    task_id: str
    session_id: str
    caller_id: str
    prompt: str
    allowed_tools: tuple[str, ...] = ()
    max_steps: int = 8
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not all((self.task_id, self.session_id, self.caller_id, self.prompt)):
            raise ValueError("task, session, caller, and prompt required")
        if self.max_steps < 1:
            raise ValueError("max_steps must be positive")

@dataclass
class HarnessResult:
    harness: str
    provider: str
    status: str
    response: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0
    error: str | None = None

class AgentHarness(Protocol):
    async def run(self, request: HarnessRequest) -> HarnessResult: ...
