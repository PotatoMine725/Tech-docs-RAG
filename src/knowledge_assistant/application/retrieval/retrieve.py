"""Query → ranked chunks (RAG-002). Embeds the question as a QUERY (the composition root passes a cached embedder),
searches one arm's store, and drops same-content duplicates.

Dedup (RAG-002 addendum 1, both arms alike): fetch `top_k + overfetch` hits, order them by (score desc, chunk_id),
keep the first hit of each `content_hash`, cut to `top_k` and number the ranks 1..k again. Same-document duplicates
are already dropped at chunking (ADR-0003 D1), so the ones dropped here are copies of one text in two documents.
`duplicates_dropped` counts the over-fetched hits dropped this way.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass

from knowledge_assistant.core.exceptions import RetrievalError
from knowledge_assistant.core.interfaces.embedding import Embedder, EmbeddingTask
from knowledge_assistant.core.interfaces.vector_store import VectorStore
from knowledge_assistant.core.models import RetrievedChunk


@dataclass(frozen=True)
class RetrievalResult:
    chunks: tuple[RetrievedChunk, ...]  # rank 1 first, ranks 1..k
    duplicates_dropped: int
    latency_ms: dict[str, float]  # embed_query, retrieve


def dedupe_by_content(hits: list[RetrievedChunk], top_k: int) -> tuple[list[RetrievedChunk], int]:
    """(the top_k unique-content hits re-ranked 1..k, number of duplicate hits dropped among `hits`)."""
    ordered = sorted(hits, key=lambda hit: (-hit.score, hit.chunk.chunk_id))
    seen: set[str] = set()
    unique: list[RetrievedChunk] = []
    for hit in ordered:
        if hit.chunk.content_hash in seen:
            continue
        seen.add(hit.chunk.content_hash)
        unique.append(hit)
    dropped = len(ordered) - len(unique)
    return [
        RetrievedChunk(chunk=hit.chunk, rank=rank, score=hit.score)
        for rank, hit in enumerate(unique[:top_k], start=1)
    ], dropped


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        top_k: int = 5,
        overfetch: int = 10,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if top_k < 1 or overfetch < 0:
            raise ValueError(f"top_k must be >= 1 and overfetch >= 0, got {top_k}, {overfetch}")
        self._embedder = embedder
        self._store = store
        self.top_k = top_k
        self.overfetch = overfetch
        self._clock = clock

    def retrieve(self, question: str) -> RetrievalResult:
        start = self._clock()
        vectors = self._embedder.embed([question], EmbeddingTask.QUERY)
        embedded = self._clock()
        if len(vectors) != 1:
            raise RetrievalError(f"expected 1 query embedding, got {len(vectors)}")
        hits = self._store.search(vectors[0], self.top_k + self.overfetch)
        searched = self._clock()
        if not hits:
            raise RetrievalError("the vector store returned no chunks (is the collection indexed?)")
        chunks, dropped = dedupe_by_content(hits, self.top_k)
        return RetrievalResult(
            chunks=tuple(chunks),
            duplicates_dropped=dropped,
            latency_ms={"embed_query": (embedded - start) * 1000.0, "retrieve": (searched - embedded) * 1000.0},
        )
