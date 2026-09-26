"""Embedding cache: a decorator around any Embedder, backed by one SQLite file (ADR-0005).

Paid vectors are written after every batch, so a crash or quota stop never loses them and
a re-run only sends the texts that are still missing.
"""

import hashlib
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path

from knowledge_assistant.core.exceptions import EmbeddingError
from knowledge_assistant.core.interfaces.embedding import Embedder, EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.throttle import estimate_tokens

SCHEMA = """
CREATE TABLE IF NOT EXISTS embeddings (
    key TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    task TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL,
    created_at TEXT NOT NULL
)
"""
LOOKUP_CHUNK = 500  # stays under SQLite's bound-parameter limit


def cache_key(model_id: str, task: EmbeddingTask, text: str) -> str:
    return hashlib.sha256(f"{model_id}|{task.value}|{text}".encode("utf-8")).hexdigest()


def _to_blob(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _from_blob(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))


class CachingEmbedder:
    """Looks every text up first; only misses reach the inner embedder, one batch at a time."""

    def __init__(self, inner: Embedder, path: str | Path, batch_size: int) -> None:
        self._inner = inner
        self._batch_size = batch_size
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute(SCHEMA)
        self._db.commit()
        self.hits = 0  # unique texts served from the cache
        self.misses = 0  # unique texts sent to the inner embedder
        self.inner_calls = 0
        self.estimated_tokens = 0  # of the misses

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    def stats(self) -> dict[str, float]:
        stats: dict[str, float] = {
            "hits": self.hits,
            "misses": self.misses,
            "inner_calls": self.inner_calls,
            "estimated_tokens": self.estimated_tokens,
        }
        inner_stats = getattr(self._inner, "stats", None)
        if callable(inner_stats):
            stats["api_requests"] = inner_stats().get("api_requests", 0)
        return stats

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "CachingEmbedder":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        keys = [cache_key(self.model_id, task, text) for text in texts]
        found = self._lookup(list(dict.fromkeys(keys)))
        self.hits += len(found)

        missing: dict[str, str] = {}  # key -> text, first occurrence order, duplicates sent once
        for key, text in zip(keys, texts):
            if key not in found and key not in missing:
                missing[key] = text
        pending = list(missing.items())
        for start in range(0, len(pending), self._batch_size):
            batch = pending[start : start + self._batch_size]
            found.update(self._embed_and_store(batch, task))

        return [found[key] for key in keys]

    def _lookup(self, keys: list[str]) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        for start in range(0, len(keys), LOOKUP_CHUNK):
            part = keys[start : start + LOOKUP_CHUNK]
            rows = self._db.execute(
                f"SELECT key, dim, vector FROM embeddings WHERE key IN ({','.join('?' * len(part))})",
                part,
            )
            for key, dim, blob in rows:
                found[key] = _from_blob(blob, dim)
        return found

    def _embed_and_store(self, batch: list[tuple[str, str]], task: EmbeddingTask) -> dict[str, list[float]]:
        texts = [text for _, text in batch]
        vectors = self._inner.embed(texts, task)
        self.inner_calls += 1
        if len(vectors) != len(texts):
            raise EmbeddingError(f"inner embedder returned {len(vectors)} vectors for {len(texts)} texts")
        self.misses += len(texts)
        self.estimated_tokens += sum(estimate_tokens(t) for t in texts)

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        stored: dict[str, list[float]] = {}
        rows = []
        for (key, _), vector in zip(batch, vectors):
            blob = _to_blob(vector)
            rows.append((key, self.model_id, task.value, len(vector), blob, now))
            stored[key] = _from_blob(blob, len(vector))  # same float32 values as a later cache hit
        with self._db:  # one transaction per batch
            self._db.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?, ?, ?, ?, ?)", rows)
        return stored
