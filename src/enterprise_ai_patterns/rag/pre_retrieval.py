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


@dataclass(frozen=True)
class RoutedQuery:
    """A retrieval query and an allowlisted logical backend name."""

    query: str
    source: str


class RuleBasedQueryPlanner(BasicQueryPlanner):
    """Deterministic example for a *bounded* manufacturing vocabulary.

    Does not resolve arbitrary language, authenticate identities, or enforce ACLs.
    Ambiguous requests retain a general document-search plan rather than inventing
    business filters. A production planner should be tested against its domain.
    """

    def plan(self, query: str) -> QueryPlan:
        base = super().plan(query)
        text = base.normalized_query.lower()
        is_orders = bool(re.search(r"\borders?\b", text))
        is_inventory = bool(re.search(r"\b(inventory|stock|shortages?|availability)\b", text))
        is_policy = bool(re.search(r"\b(escalat(?:ion|e)|polic(?:y|ies))\b", text))
        filters: dict[str, str] = {}
        # Only known, explicit locations/statuses are extracted. Never treat these
        # filters as a substitute for caller-specific server-side authorization.
        if re.search(r"\b(florida|fl)\b", text):
            filters["region"] = "FL"
        if re.search(r"\bopen\s+(?:manufacturing\s+)?orders?\b", text):
            filters["order_status"] = "open"

        parts = []
        if is_orders:
            parts.append("open manufacturing orders" if filters.get("order_status") == "open" else "manufacturing orders")
        if is_inventory:
            parts.append("inventory availability and shortages")
        if is_policy:
            parts.append("shortage escalation policy")
        if not parts:
            return QueryPlan(base.original_query, base.normalized_query,
                             base.retrieval_queries, base.intent, filters)
        intent = "order_exception_analysis" if is_orders and is_inventory else (
            "inventory_lookup" if is_inventory else "order_lookup" if is_orders else "policy_lookup")
        return QueryPlan(base.original_query, base.normalized_query,
                         tuple(dict.fromkeys(parts + list(base.retrieval_queries))), intent, filters)

    def routed_queries(self, plan: QueryPlan) -> tuple[RoutedQuery, ...]:
        """Resolve only known query templates to fixed source names.

        Unrecognized expansions go to document search, never an arbitrary URL.
        """
        result = []
        for query in plan.retrieval_queries:
            if query in ("manufacturing orders", "open manufacturing orders"):
                source = "erp_orders"
            elif query == "inventory availability and shortages":
                source = "inventory"
            else:
                source = "policy_documents"
            result.append(RoutedQuery(query, source))
        return tuple(result)
