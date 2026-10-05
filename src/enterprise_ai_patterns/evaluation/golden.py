from __future__ import annotations

from dataclasses import dataclass

from .metrics import precision_at_k, recall_at_k, reciprocal_rank


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    query: str
    expected_source_ids: tuple[str, ...]
    forbidden_source_ids: tuple[str, ...] = ()
    expected_label: str | None = None
    must_abstain: bool = False


@dataclass(frozen=True)
class Observation:
    retrieved_source_ids: tuple[str, ...]
    cited_source_ids: tuple[str, ...]
    predicted_label: str | None = None
    abstained: bool = False


def evaluate_case(case: GoldenCase, observation: Observation, *, k: int = 5) -> dict[str, float | bool | str]:
    relevant = set(case.expected_source_ids)
    retrieved = list(observation.retrieved_source_ids)
    forbidden = set(case.forbidden_source_ids)
    citation_set = set(observation.cited_source_ids)

    retrieval_recall = recall_at_k(retrieved, relevant, k)
    retrieval_precision = precision_at_k(retrieved, relevant, k)
    mrr = reciprocal_rank(retrieved, relevant)
    forbidden_ok = not bool(set(retrieved) & forbidden)
    citations_valid = citation_set.issubset(set(retrieved))
    label_ok = case.expected_label is None or observation.predicted_label == case.expected_label
    abstention_ok = observation.abstained == case.must_abstain

    passed = (
        retrieval_recall == 1.0
        and forbidden_ok
        and citations_valid
        and label_ok
        and abstention_ok
    )

    return {
        "case_id": case.case_id,
        "passed": passed,
        "recall_at_k": retrieval_recall,
        "precision_at_k": retrieval_precision,
        "mrr": mrr,
        "forbidden_ok": forbidden_ok,
        "citations_valid": citations_valid,
        "label_ok": label_ok,
        "abstention_ok": abstention_ok,
    }
