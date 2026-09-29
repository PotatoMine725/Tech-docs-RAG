"""Offline test doubles shared across tasks."""

import hashlib
import math
from types import SimpleNamespace

from google.genai import errors

from knowledge_assistant.core.interfaces.embedding import EmbeddingTask


class FakeEmbedder:
    """Deterministic unit vectors derived from a hash of (task, text). Counts calls; no network.

    Plans calls of at most `batch_size` texts, like a provider embedder with a count limit.
    """

    def __init__(self, dim: int = 8, model_id: str = "fake-embedder@8", batch_size: int = 10) -> None:
        self.dim = dim
        self._model_id = model_id
        self.batch_size = batch_size
        self.calls: list[tuple[list[str], EmbeddingTask]] = []

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def texts_embedded(self) -> int:
        return sum(len(texts) for texts, _ in self.calls)

    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        return [texts[i : i + self.batch_size] for i in range(0, len(texts), self.batch_size)]

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


class FakeClock:
    """One clock for the throttle and every sleep: sleeping moves time forward."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeModels:
    """Stands in for genai client.models.

    `script` holds exceptions to raise, in order, before succeeding. `fail_from_call` (1-based) makes
    that HTTP call and every later one raise `failure`.
    """

    def __init__(
        self,
        dim: int = 4,
        script: list[Exception] | None = None,
        raw: list[float] | None = None,
        fail_from_call: int | None = None,
        failure: Exception | None = None,
        clock: FakeClock | None = None,
    ):
        self.dim = dim
        self.script = list(script or [])
        self.raw = raw
        self.fail_from_call = fail_from_call
        self.failure = failure
        self.clock = clock
        self.calls: list[dict] = []

    def embed_content(self, *, model, contents, config):
        self.calls.append(
            {"model": model, "contents": list(contents), "config": config, "at": self.clock() if self.clock else 0.0}
        )
        if self.fail_from_call is not None and len(self.calls) >= self.fail_from_call:
            raise self.failure
        if self.script:
            raise self.script.pop(0)
        values = self.raw or [3.0, 4.0] + [0.0] * (self.dim - 2)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=list(values)) for _ in contents])


def api_error(code: int = 503, retry_delay: str | None = None, quota_id: str | None = None) -> errors.APIError:
    """An APIError with the google.rpc body shape: optional RetryInfo and QuotaFailure details."""
    status = {429: "RESOURCE_EXHAUSTED", 400: "INVALID_ARGUMENT"}.get(code, "UNAVAILABLE")
    error: dict = {"code": code, "status": status, "message": "test error"}
    details = []
    if quota_id:
        details.append(
            {
                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                "violations": [{"quotaMetric": "generativelanguage.googleapis.com/test_metric", "quotaId": quota_id}],
            }
        )
    if retry_delay:
        details.append({"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay})
    if details:
        error["details"] = details
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code, {"error": error})


def make_chunk(
    source_id: str = "01",
    index: int = 0,
    text: str = "Some text.",
    heading_path: tuple[str, ...] = ("Doc", "Section"),
    char_start: int = 0,
    char_end: int | None = None,
    document_name: str | None = None,
    config: str = "header-1600",
    content_hash: str | None = None,
):
    """A DocumentChunk shaped like the chunk builder's (embed_text = heading line + blank line + body)."""
    from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, DocumentChunk

    heading = HEADING_PATH_SEPARATOR.join(heading_path)
    return DocumentChunk(
        chunk_id=f"{source_id}:{config}:{index:04d}",
        source_id=source_id,
        document_name=document_name or f"Document {source_id}",
        source_url=f"https://example.invalid/{source_id}",
        heading_path=heading_path,
        location_type="heading",
        char_start=char_start,
        char_end=char_start + len(text) if char_end is None else char_end,
        display_text=text,
        embed_text=f"{heading}\n\n{text}" if heading else text,
        content_hash=content_hash or hashlib.sha256(text.encode("utf-8")).hexdigest(),
        chunker_config=config,
    )


class InMemoryVectorStore:
    """VectorStore double: dot-product scores (unit vectors → cosine), highest first, insertion order on ties.

    `scores` (chunk_id → score) overrides the computed score, to script exact rankings and ties.
    """

    def __init__(self, scores: dict[str, float] | None = None) -> None:
        self._items: list[tuple] = []
        self.scores = scores or {}
        self.searches: list[int] = []

    def upsert(self, chunks, embeddings) -> None:
        ids = {chunk.chunk_id for chunk in chunks}
        self._items = [item for item in self._items if item[0].chunk_id not in ids]
        self._items.extend(zip(chunks, embeddings))

    def search(self, embedding, top_k):
        from knowledge_assistant.core.models import RetrievedChunk

        self.searches.append(top_k)
        scored = [
            (self.scores.get(chunk.chunk_id, sum(a * b for a, b in zip(embedding, vector))), chunk)
            for chunk, vector in self._items
        ]
        scored.sort(key=lambda item: -item[0])  # stable: insertion order on ties
        return [RetrievedChunk(chunk=chunk, rank=rank, score=score)
                for rank, (score, chunk) in enumerate(scored[:top_k], start=1)]

    def count(self) -> int:
        return len(self._items)

    def get_ids(self) -> set[str]:
        return {chunk.chunk_id for chunk, _ in self._items}


class FakeLLM:
    """LLM double: returns the scripted texts in order (the last one repeats) and records every request."""

    def __init__(self, *texts: str, model: str = "fake-llm") -> None:
        self.texts = list(texts)
        self.model = model
        self.requests: list = []

    def generate(self, request):
        from knowledge_assistant.core.interfaces.llm import LLMResponse

        self.requests.append(request)
        text = self.texts[min(len(self.requests), len(self.texts)) - 1]
        return LLMResponse(text=text, model_used=self.model, retry_count=0, fallback_used=False,
                           prompt_tokens=len(request.prompt) // 4, output_tokens=len(text) // 4, latency_ms=1.0)
