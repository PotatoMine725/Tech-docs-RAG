"""Embedding cache: a decorator around any Embedder, backed by one SQLite file (ADR-0005).

Misses are sent in the groups the inner embedder plans (`plan_calls`), one provider call per group,
and each group's vectors are committed before the next group is sent. A crash or quota stop therefore
never loses a paid call's vectors, and a re-run only sends the texts that are still missing.
"""

import hashlib
import sqlite3
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

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


class PlannedEmbedder(Embedder, Protocol):
    """An Embedder that also says how it splits texts into provider calls (a batching detail, so not core)."""

    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        """How `embed` splits `texts` into provider calls, in order.

        `embed(group)` on one returned group makes exactly one provider call, so a caller that
        stores results per group (the embedding cache) keeps every paid call's vectors.
        """
        ...


class CachingEmbedder:
    """Looks every text up first; only misses reach the inner embedder, one planned call at a time.

    Satisfies the core `Embedder` protocol (`model_id`, `embed`).
    """

    def __init__(self, inner: PlannedEmbedder, path: str | Path) -> None:
        self._inner = inner
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
        # The inner embedder owns the split rule (count and token caps); the cache never re-slices,
        # so a group here is exactly one paid call and is committed before the next one is sent.
        pending = list(missing.items())
        start = 0
        for group in self._inner.plan_calls([text for _, text in pending]):
            batch = pending[start : start + len(group)]
            start += len(group)
            if [text for _, text in batch] != list(group):
                raise EmbeddingError("inner plan_calls must return every text once, in order")
            found.update(self._embed_and_store(batch, task))
        if start != len(pending):
            raise EmbeddingError(f"inner plan_calls covered {start} of {len(pending)} texts")

        return [found[key] for key in keys]

    def missing(self, texts: list[str], task: EmbeddingTask) -> list[str]:
        """The unique texts `embed` would send to the inner embedder (first-occurrence order). No API call."""
        keys = [cache_key(self.model_id, task, text) for text in texts]
        found = self._lookup(list(dict.fromkeys(keys)))
        missing: dict[str, str] = {}
        for key, text in zip(keys, texts):
            if key not in found and key not in missing:
                missing[key] = text
        return list(missing.values())

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
        with self._db:  # one transaction per provider call
            self._db.executemany("INSERT OR REPLACE INTO embeddings VALUES (?, ?, ?, ?, ?, ?)", rows)
        return stored
