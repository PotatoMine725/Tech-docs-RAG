"""Offline test doubles shared across tasks."""

import hashlib
import math

from knowledge_assistant.core.interfaces.embedding import EmbeddingTask


class FakeEmbedder:
    """Deterministic unit vectors derived from a hash of (task, text). Counts calls; no network."""

    def __init__(self, dim: int = 8, model_id: str = "fake-embedder@8") -> None:
        self.dim = dim
        self._model_id = model_id
        self.calls: list[tuple[list[str], EmbeddingTask]] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def texts_embedded(self) -> int:
        return sum(len(texts) for texts, _ in self.calls)

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        self.calls.append((list(texts), task))
        return [self.vector(text, task) for text in texts]

    def vector(self, text: str, task: EmbeddingTask = EmbeddingTask.DOCUMENT) -> list[float]:
        digest = b""
        block = 0
        while len(digest) < self.dim:
            digest += hashlib.sha256(f"{block}|{task.value}|{text}".encode("utf-8")).digest()
            block += 1
        raw = [digest[i] - 127.5 for i in range(self.dim)]
        norm = math.sqrt(sum(v * v for v in raw))
        return [v / norm for v in raw]
