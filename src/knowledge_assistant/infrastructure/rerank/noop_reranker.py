"""The `none` reranker (RERANK_PROVIDER default): keeps the retriever's order. Its scores are positions, not relevance,
so `absolute_scores` is false and the retriever does not call it (ADR-0009)."""
from knowledge_assistant.core.interfaces.reranker import RerankResult


class NoOpReranker:
    @property
    def model_id(self) -> str:
        return "none"

    @property
    def absolute_scores(self) -> bool:
        return False

    def rerank(self, query: str, passages: list[str], top_n: int | None = None) -> list[RerankResult]:
        count = len(passages) if top_n is None else max(0, min(top_n, len(passages)))
        # Descending dummy scores, so a caller that sorts by score keeps the original order.
        return [RerankResult(index=i, score=float(len(passages) - i)) for i in range(count)]
