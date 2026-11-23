"""Reranking contract: reorder retrieved passages by relevance to the query. Separate from embedding and generation,
so each can come from its own provider (a cross-encoder, a local LLM, or none)."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RerankResult:
    """One passage after reranking: `index` into the passages given to `rerank`, and the reranker's own score
    (only comparable between results of one call)."""

    index: int
    score: float


class Reranker(Protocol):
    @property
    def model_id(self) -> str: ...

    def rerank(self, query: str, passages: list[str], top_n: int | None = None) -> list[RerankResult]:
        """Best first; at most `top_n` results (all when None)."""
        ...
