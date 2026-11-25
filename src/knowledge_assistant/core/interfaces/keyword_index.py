"""Keyword (sparse) index contract: BM25-style search over chunk text (ADR-0007). Separate from `VectorStore`: it
needs no embedding, so one keyword index per arm serves every embedding provider."""
from typing import Protocol

from knowledge_assistant.core.models import DocumentChunk, RetrievedChunk


class KeywordIndex(Protocol):
    """One index of chunk texts (one per experiment arm, keyed by the chunker config like the vector collection)."""

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        """Insert or replace chunks by `chunk_id`."""
        ...

    def delete_source(self, source_id: str) -> int:
        """Remove every chunk of one source document; returns how many were removed."""
        ...

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        """The `top_k` best keyword matches for the raw question, rank 1 first; `score` is higher = better and only
        comparable within one call. No match returns an empty list."""
        ...

    def count(self) -> int: ...

    def get_ids(self) -> set[str]: ...
