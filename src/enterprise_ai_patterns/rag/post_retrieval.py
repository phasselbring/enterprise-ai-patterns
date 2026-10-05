from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .pipeline import Chunk


@dataclass(frozen=True)
class ContextBundle:
    chunks: tuple[Chunk, ...]
    rendered: str


class ContextBuilder:
    """Deduplicates and packs selected evidence into a bounded context window."""

    def __init__(self, *, max_chars: int = 12_000) -> None:
        self._max_chars = max_chars

    def build(self, chunks: Iterable[Chunk]) -> ContextBundle:
        selected: list[Chunk] = []
        rendered_parts: list[str] = []
        seen: set[str] = set()
        used = 0

        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            block = f"[{chunk.chunk_id}] {chunk.text.strip()}"
            if used + len(block) > self._max_chars:
                break
            seen.add(chunk.chunk_id)
            selected.append(chunk)
            rendered_parts.append(block)
            used += len(block)

        return ContextBundle(tuple(selected), "\n\n".join(rendered_parts))
