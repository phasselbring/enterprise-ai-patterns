from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .pipeline import Chunk


@dataclass(frozen=True)
class Claim:
    text: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class GeneratedAnswer:
    text: str
    claims: tuple[Claim, ...]


@dataclass(frozen=True)
class GroundingResult:
    ok: bool
    invalid_source_ids: tuple[str, ...] = ()
    unsupported_claims: tuple[str, ...] = ()


class EvidenceSupportModel(Protocol):
    def supports(self, claim: str, evidence: str) -> bool: ...


class GroundingChecker:
    """Validates source identity *and*, optionally, claim/evidence support.

    Citation identity checking alone does not prove the prose is grounded. Supplying a support
    model (NLI model, LLM judge with a frozen rubric, etc.) adds the semantic support check.
    """

    def __init__(self, support_model: EvidenceSupportModel | None = None) -> None:
        self._support_model = support_model

    def check(self, answer: GeneratedAnswer, chunks: Sequence[Chunk]) -> GroundingResult:
        by_id = {c.chunk_id: c for c in chunks}
        invalid: list[str] = []
        unsupported: list[str] = []

        for claim in answer.claims:
            if not claim.source_ids:
                unsupported.append(claim.text)
                continue

            missing = [source_id for source_id in claim.source_ids if source_id not in by_id]
            invalid.extend(missing)
            if missing:
                continue

            if self._support_model is not None:
                evidence = "\n".join(by_id[source_id].text for source_id in claim.source_ids)
                if not self._support_model.supports(claim.text, evidence):
                    unsupported.append(claim.text)

        return GroundingResult(
            ok=not invalid and not unsupported,
            invalid_source_ids=tuple(dict.fromkeys(invalid)),
            unsupported_claims=tuple(unsupported),
        )
