"""Indexing use case: chunk file -> embeddings -> vector store (RAG-001b, ADR-0005).

Depends on core interfaces only; `scripts/ingestion/build_index.py` wires the Gemini embedder,
the embedding cache and the Chroma store.
"""
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from knowledge_assistant.application.ingestion.build_chunks import load_chunks
from knowledge_assistant.core.interfaces.embedding import Embedder, EmbeddingTask
from knowledge_assistant.core.interfaces.vector_store import VectorStore
from knowledge_assistant.core.models import DocumentChunk

Usage = Callable[[], Mapping[str, float]]


@dataclass(frozen=True)
class IndexReport:
    started_at: str  # UTC, ISO 8601
    chunks_file: str
    chunker_config: str
    embedding_model_id: str
    chunks_total: int  # lines in the chunk file
    already_present: int  # chunk_ids already in the store (skipped: resume)
    newly_embedded: int  # chunks embedded and upserted by this run
    cache_hits: int | None  # unique texts served by the embedding cache (None: no usage counters wired)
    api_texts: int | None  # unique texts sent to the provider
    api_requests: int | None  # provider quota requests (V-1: one per text)
    estimated_tokens: int | None  # chars/4 of the texts sent to the provider
    duration_s: float
    store_count: int  # store.count() after the run

    def to_dict(self) -> dict:
        return asdict(self)


def chunker_config_of(chunks: list[DocumentChunk]) -> str:
    """The one chunker config of a chunk file; a file mixing arms is an error."""
    configs = {chunk.chunker_config for chunk in chunks}
    if len(configs) != 1:
        raise ValueError(f"expected one chunker_config per chunk file, found {sorted(configs)}")
    return configs.pop()


class IndexCorpus:
    """Embeds the chunks the store does not have yet and upserts them.

    All pending texts go to the embedder in one `embed` call: the embedder (and the cache around it)
    owns the split into provider calls, so the throughput planned in ADR-0005 D15 holds. The upsert
    into the store is batched. A run stopped by the quota upserts nothing, but every paid vector is
    already in the embedding cache, so the re-run costs no quota for them.
    """

    def __init__(
        self,
        embedder: Embedder,
        store: VectorStore,
        upsert_batch: int = 100,
        usage: Usage | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._upsert_batch = upsert_batch
        self._usage = usage
        self._clock = clock

    def pending(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Chunks whose chunk_id is not in the store yet, in file order."""
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("chunk file has duplicate chunk_ids")
        present = self._store.get_ids()
        return [chunk for chunk in chunks if chunk.chunk_id not in present]

    def run(self, chunks_path: Path) -> IndexReport:
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        start = self._clock()
        before = dict(self._usage()) if self._usage else {}

        chunks = load_chunks(chunks_path)
        config = chunker_config_of(chunks)
        todo = self.pending(chunks)
        if todo:
            vectors = self._embedder.embed([chunk.embed_text for chunk in todo], EmbeddingTask.DOCUMENT)
            if len(vectors) != len(todo):
                raise ValueError(f"embedder returned {len(vectors)} vectors for {len(todo)} chunks")
            for i in range(0, len(todo), self._upsert_batch):
                self._store.upsert(todo[i : i + self._upsert_batch], vectors[i : i + self._upsert_batch])

        after = dict(self._usage()) if self._usage else {}

        def delta(key: str) -> int | None:
            return int(after.get(key, 0) - before.get(key, 0)) if self._usage else None

        return IndexReport(
            started_at=started_at,
            chunks_file=chunks_path.name,
            chunker_config=config,
            embedding_model_id=self._embedder.model_id,
            chunks_total=len(chunks),
            already_present=len(chunks) - len(todo),
            newly_embedded=len(todo),
            cache_hits=delta("hits"),
            api_texts=delta("misses"),
            api_requests=delta("api_requests"),
            estimated_tokens=delta("estimated_tokens"),
            duration_s=round(self._clock() - start, 3),
            store_count=self._store.count(),
        )
