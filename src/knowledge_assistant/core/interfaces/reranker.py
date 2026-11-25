"""Reranking contract: reorder retrieved passages by relevance to the query. Separate from embedding and generation,
so each can come from its own provider (a cross-encoder, a local LLM, or none)."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RerankResult:
    """One passage after reranking: `index` into the passages given to `rerank`, and the reranker's own score.

    When the reranker's `absolute_scores` is true the score is a fixed-scale relevance (a cross-encoder's
    sigmoid(logit), 0..1) that can be compared across calls, so a gate may read it (ADR-0009). Otherwise it only
    orders the results of one call and must never reach a gate."""

    index: int
    score: float


class Reranker(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def absolute_scores(self) -> bool:
        """True when scores mean the same thing in every call (see RerankResult)."""
        ...

    def rerank(self, query: str, passages: list[str], top_n: int | None = None) -> list[RerankResult]:
        """Best first; at most `top_n` results (all when None)."""
        ...
