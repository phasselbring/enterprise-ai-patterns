from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


_ALLOWED_ROLES = {"system", "user", "assistant"}


@dataclass(frozen=True)
class ChatTurn:
    role: str
    content: str


@dataclass(frozen=True)
class ChatExample:
    messages: tuple[ChatTurn, ...]

    def validate(self) -> None:
        if not self.messages:
            raise ValueError("example must contain messages")
        for message in self.messages:
            if message.role not in _ALLOWED_ROLES:
                raise ValueError(f"unsupported role: {message.role}")
            if not message.content.strip():
                raise ValueError("message content cannot be empty")
        if self.messages[-1].role != "assistant":
            raise ValueError("supervised chat example must end with the target assistant response")

    def to_record(self) -> dict:
        self.validate()
        return {
            "messages": [
                {"role": message.role, "content": message.content}
                for message in self.messages
            ]
        }


def write_jsonl(examples: list[ChatExample], path: str | Path) -> None:
    target = Path(path)
    with target.open("w", encoding="utf-8") as handle:
        for example in examples:
            handle.write(json.dumps(example.to_record(), ensure_ascii=False) + "\n")
