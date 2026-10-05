from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol
import re


@dataclass(frozen=True)
class QueryPlan:
    original_query: str
    normalized_query: str
    retrieval_queries: tuple[str, ...]
    intent: str = "general"
    metadata_filters: dict[str, str] = field(default_factory=dict)


class QueryPlanner(Protocol):
    def plan(self, query: str) -> QueryPlan: ...


class BasicQueryPlanner:
    """Small deterministic planner for tests/examples.

    Production implementations commonly replace or augment this with a classifier or LLM
    that can rewrite, decompose, route, and apply domain metadata constraints.
    """

    def __init__(
        self,
        *,
        intent_classifier: Callable[[str], str] | None = None,
        query_expander: Callable[[str], list[str]] | None = None,
    ) -> None:
        self._intent_classifier = intent_classifier or (lambda _: "general")
        self._query_expander = query_expander or (lambda _: [])

    def plan(self, query: str) -> QueryPlan:
        normalized = re.sub(r"\s+", " ", query).strip()
        if not normalized:
            raise ValueError("query cannot be empty")

        expansions = [q.strip() for q in self._query_expander(normalized) if q.strip()]
        retrieval_queries = tuple(dict.fromkeys([normalized, *expansions]))

        return QueryPlan(
            original_query=query,
            normalized_query=normalized,
            retrieval_queries=retrieval_queries,
            intent=self._intent_classifier(normalized),
        )
