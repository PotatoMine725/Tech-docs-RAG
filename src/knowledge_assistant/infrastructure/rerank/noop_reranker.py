"""The `none` reranker: keeps the retriever's order. A placeholder until hybrid search brings a real reranker."""
from knowledge_assistant.core.interfaces.reranker import RerankResult


class NoOpReranker:
    @property
    def model_id(self) -> str:
        return "none"

    def rerank(self, query: str, passages: list[str], top_n: int | None = None) -> list[RerankResult]:
        count = len(passages) if top_n is None else max(0, min(top_n, len(passages)))
        # Descending dummy scores, so a caller that sorts by score keeps the original order.
        return [RerankResult(index=i, score=float(len(passages) - i)) for i in range(count)]
