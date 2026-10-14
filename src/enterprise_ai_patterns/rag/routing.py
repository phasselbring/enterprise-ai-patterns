"""Explicit source routing with no arbitrary model-controlled connector names."""
from __future__ import annotations

from typing import Mapping

from .pre_retrieval import RoutedQuery


class RetrievalRouter:
    """Dispatch to trusted retrieval adapters; all must enforce caller ACLs.

    Each adapter implements search(query, *, limit, caller, metadata_filters).
    Backends MUST push caller ACL and metadata predicates into the data query
    before applying limit; post-filtering is not an acceptable implementation.
    """

    def __init__(self, sources: Mapping[str, object]) -> None:
        self._sources = dict(sources)

    def search(self, routed: RoutedQuery, *, caller, limit: int = 20,
               metadata_filters: Mapping[str, str] | None = None):
        try:
            backend = self._sources[routed.source]
        except KeyError as exc:
            raise ValueError(f"Unconfigured retrieval source: {routed.source}") from exc
        if caller is None or not getattr(caller, "user_id", None):
            raise PermissionError("Authenticated caller required")
        return backend.search(routed.query, limit=limit, caller=caller,
                              metadata_filters=dict(metadata_filters or {}))
