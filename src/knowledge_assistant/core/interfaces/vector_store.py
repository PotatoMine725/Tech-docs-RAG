from typing import Protocol

from knowledge_assistant.core.models import DocumentChunk


class VectorStore(Protocol):
    def add(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None: ...

    def search(self, embedding: list[float], top_k: int) -> list[DocumentChunk]: ...
