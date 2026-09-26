from typing import Protocol

from knowledge_assistant.core.models import DocumentChunk, RetrievedChunk


class VectorStore(Protocol):
    """One collection of chunk vectors (one per experiment arm, ADR-0003 D7)."""

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        """Insert or replace chunks by `chunk_id`; `embeddings[i]` belongs to `chunks[i]`."""
        ...

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """The `top_k` most similar chunks, rank 1 first."""
        ...

    def count(self) -> int: ...

    def get_ids(self) -> set[str]: ...
