"""Portable synthetic scenario specification."""
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Scenario:
    name: str
    prompt: str
    caller_id: str = "demo-user"
    expected_text: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
