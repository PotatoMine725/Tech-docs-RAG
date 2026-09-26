"""Gemini embedder behind core.interfaces.embedding (ADR-0004 D10, ADR-0005).

Batches texts, throttles to the per-minute limits, retries transient errors with backoff,
and L2-normalizes vectors below the model's full size.
"""

import math
import random
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from google import genai
from google.genai import errors, types

from knowledge_assistant.config import EmbeddingSettings, get_embedding_settings, get_gemini_api_key
from knowledge_assistant.core.exceptions import ConfigurationError, EmbeddingError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens

TASK_TYPES = {
    EmbeddingTask.DOCUMENT: "RETRIEVAL_DOCUMENT",
    EmbeddingTask.QUERY: "RETRIEVAL_QUERY",
}
FULL_DIM = 3072  # only full-size vectors come back normalized
RETRYABLE_STATUS = {429, 500, 503, 504}
BACKOFF_BASE_S = 1.0  # 1, 2, 4, 8 ... seconds


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise EmbeddingError("provider returned a zero vector")
    return [v / norm for v in vector]


def _retry_after_s(error: errors.APIError) -> float | None:
    """Server-suggested wait: HTTP Retry-After header, or google.rpc.RetryInfo retryDelay."""
    headers = getattr(error.response, "headers", None)
    if headers is not None:
        value = headers.get("retry-after")
        if value:
            try:
                return float(value)
            except ValueError:
                pass
    details = error.details.get("error", error.details) if isinstance(error.details, dict) else {}
    for item in details.get("details", []) if isinstance(details, dict) else []:
        delay = item.get("retryDelay") if isinstance(item, dict) else None
        match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(delay)) if delay else None
        if match:
            return float(match.group(1))
    return None


class GeminiEmbedder:
    def __init__(
        self,
        settings: EmbeddingSettings | None = None,
        client: Any = None,
        throttle: SlidingWindowThrottle | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._settings = settings or get_embedding_settings()
        self._client = client
        self._throttle = throttle or SlidingWindowThrottle(
            self._settings.requests_per_minute, self._settings.tokens_per_minute
        )
        self._sleep = sleep
        self._jitter = jitter
        self.api_requests = 0  # HTTP attempts, retries included (quota accounting)
        self.retries = 0
        self.estimated_tokens = 0

    @property
    def model_id(self) -> str:
        return self._settings.model_id

    def stats(self) -> dict[str, float]:
        return {
            "api_requests": self.api_requests,
            "retries": self.retries,
            "estimated_tokens": self.estimated_tokens,
            "throttle_wait_s": round(self._throttle.total_wait_s, 3),
        }

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in self._batches(texts):
            vectors.extend(self._embed_batch(batch, task))
        return vectors

    def _batches(self, texts: list[str]) -> list[list[str]]:
        """At most `batch_size` texts and at most one minute of estimated tokens per request."""
        batches: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for text in texts:
            tokens = estimate_tokens(text)
            if current and (
                len(current) >= self._settings.batch_size
                or current_tokens + tokens > self._settings.tokens_per_minute
            ):
                batches.append(current)
                current, current_tokens = [], 0
            current.append(text)
            current_tokens += tokens
        if current:
            batches.append(current)
        return batches

    def _get_client(self) -> Any:
        if self._client is None:
            api_key = get_gemini_api_key()
            if not api_key:
                raise ConfigurationError("GEMINI_API_KEY is not set")
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=int(self._settings.timeout_s * 1000)),
            )
        return self._client

    def _embed_batch(self, batch: list[str], task: EmbeddingTask) -> list[list[float]]:
        client = self._get_client()
        tokens = sum(estimate_tokens(t) for t in batch)
        config = types.EmbedContentConfig(
            task_type=TASK_TYPES[task], output_dimensionality=self._settings.dim
        )
        attempts = self._settings.max_attempts
        for attempt in range(1, attempts + 1):
            self._throttle.acquire(tokens)
            self.api_requests += 1
            self.estimated_tokens += tokens
            try:
                response = client.models.embed_content(
                    model=self._settings.model, contents=batch, config=config
                )
                return self._validate(response, len(batch))
            except errors.APIError as error:
                if error.code not in RETRYABLE_STATUS:
                    raise EmbeddingError(f"embedding request failed: HTTP {error.code} {error.status}") from error
                last_error: Exception = error
                retry_after = _retry_after_s(error)
            except (httpx.TimeoutException, TimeoutError) as error:
                last_error = error
                retry_after = None
            if attempt == attempts:
                break
            backoff = BACKOFF_BASE_S * 2 ** (attempt - 1) + self._jitter()
            self.retries += 1
            self._sleep(max(backoff, retry_after or 0.0))
        raise EmbeddingError(
            f"embedding request failed after {attempts} attempts: {type(last_error).__name__} {last_error}"
        ) from last_error

    def _validate(self, response: Any, expected: int) -> list[list[float]]:
        embeddings = response.embeddings or []
        if len(embeddings) != expected:
            raise EmbeddingError(f"expected {expected} embeddings, got {len(embeddings)}")
        vectors = []
        for embedding in embeddings:
            values = list(embedding.values or [])
            if len(values) != self._settings.dim:
                raise EmbeddingError(f"expected dimension {self._settings.dim}, got {len(values)}")
            vectors.append(l2_normalize(values) if self._settings.dim < FULL_DIM else values)
        return vectors
