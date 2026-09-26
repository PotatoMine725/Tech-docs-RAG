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
