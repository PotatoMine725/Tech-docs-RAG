"""Gemini embedder behind core.interfaces.embedding (ADR-0004 D10, ADR-0005).

Batches texts, throttles to the per-minute limits, retries transient errors with backoff,
stops at once when the daily quota is used up, and L2-normalizes vectors below the model's full size.
"""

import json
import logging
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
from knowledge_assistant.core.exceptions import ConfigurationError, EmbeddingError, QuotaExhaustedError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle, estimate_tokens

TASK_TYPES = {
    EmbeddingTask.DOCUMENT: "RETRIEVAL_DOCUMENT",
    EmbeddingTask.QUERY: "RETRIEVAL_QUERY",
}
FULL_DIM = 3072  # only full-size vectors come back normalized
RETRYABLE_STATUS = {429, 500, 503, 504}
BACKOFF_BASE_S = 1.0  # 1, 2, 4, 8 ... seconds
MAX_RETRY_WAIT_S = 120.0  # a server retry-after above this is cut, so a run never hangs silently
DAILY_RESET = "14:00 UTC+7"  # free-tier daily quota reset (ADR-0005 D19)
DAILY_QUOTA = re.compile(r"per[ _-]?day|daily", re.IGNORECASE)
API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z_\-]{35}")  # Google API key shape

logger = logging.getLogger(__name__)


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0.0:
        raise EmbeddingError("provider returned a zero vector")
    return [v / norm for v in vector]


def _error_details(error: errors.APIError) -> list[dict]:
    """The google.rpc detail objects of an API error body ({"error": {"details": [...]}})."""
    body = error.details.get("error", error.details) if isinstance(error.details, dict) else {}
    details = body.get("details", []) if isinstance(body, dict) else []
    return [item for item in details if isinstance(item, dict)] if isinstance(details, list) else []


def redact_key(text: str) -> str:
    """Remove the configured key and anything shaped like a Google API key before text is logged."""
    api_key = get_gemini_api_key()
    if api_key:
        text = text.replace(api_key, "[REDACTED]")
    return API_KEY_PATTERN.sub("[REDACTED]", text)


def _raw_body(error: errors.APIError) -> str:
    try:
        return json.dumps(error.details, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return repr(error.details)


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
    for item in _error_details(error):
        delay = item.get("retryDelay")
        match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(delay)) if delay else None
        if match:
            return float(match.group(1))
    return None


def _daily_quota_id(error: errors.APIError) -> str | None:
    """The per-day quota a 429 names in its google.rpc.QuotaFailure violations, if any.

    Per-minute 429s carry a QuotaFailure too (e.g. "...PerMinute..."); only a per-day quota id or
    metric counts. Built from the documented error shape; not yet seen in a real response.
    """
    for item in _error_details(error):
        if "QuotaFailure" not in str(item.get("@type", "")):
            continue
        for violation in item.get("violations") or []:
            if not isinstance(violation, dict):
                continue
            for field in ("quotaId", "quotaMetric"):
                value = str(violation.get(field) or "")
                if DAILY_QUOTA.search(value):
                    return value
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
        self.http_calls = 0  # HTTP attempts, retries included
        self.api_requests = 0  # quota requests: V-1 showed every text in a call counts as one
        self.retries = 0
        self.estimated_tokens = 0
        self._logged_first_429 = False  # the first 429's raw body is logged once (RAG-001b Step 0b)

    @property
    def model_id(self) -> str:
        return self._settings.model_id

    def stats(self) -> dict[str, float]:
        return {
            "http_calls": self.http_calls,
            "api_requests": self.api_requests,
            "retries": self.retries,
            "estimated_tokens": self.estimated_tokens,
            "throttle_wait_s": round(self._throttle.total_wait_s, 3),
        }

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in self.plan_calls(texts):
            vectors.extend(self._embed_batch(batch, task))
        return vectors

    def plan_calls(self, texts: list[str]) -> list[list[str]]:
        """At most `batch_size` texts (and the per-minute request limit) and half a minute of tokens per call.

        The throttle admits whole calls, so a call over half the token budget would leave the rest of
        the window unused (ADR-0005 D15): two 45-text Arm B calls (~32K) cannot share a 25K window.
        Greedy, so planning one returned group again gives back that same group: `embed(group)` is one call.
        """
        max_texts = min(self._settings.batch_size, self._settings.requests_per_minute)
        max_tokens = max(1, self._settings.tokens_per_minute // 2)
        batches: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0
        for text in texts:
            tokens = estimate_tokens(text)
            if current and (len(current) >= max_texts or current_tokens + tokens > max_tokens):
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
            self._throttle.acquire(tokens, requests=len(batch))
            self.http_calls += 1
            self.api_requests += len(batch)
            self.estimated_tokens += tokens
            try:
                response = client.models.embed_content(
                    model=self._settings.model, contents=batch, config=config
                )
                return self._validate(response, len(batch))
            except errors.APIError as error:
                if error.code == 429 and not self._logged_first_429:
                    # Logged before the daily-quota check so the classifier can be checked against a real body.
                    self._logged_first_429 = True
                    logger.warning("first HTTP 429 of this run, raw error body: %s", redact_key(_raw_body(error)))
                quota_id = _daily_quota_id(error) if error.code == 429 else None
                if quota_id:
                    raise QuotaExhaustedError(
                        f"daily embedding quota exhausted ({quota_id}); resume after the {DAILY_RESET} reset"
                    ) from error
                if error.code not in RETRYABLE_STATUS:
                    raise EmbeddingError(f"embedding request failed: HTTP {error.code} {error.status}") from error
                last_error: Exception = error
                retry_after = _retry_after_s(error)
                reason = f"HTTP {error.code} {error.status}"
            except (httpx.TimeoutException, TimeoutError) as error:
                last_error = error
                retry_after = None
                reason = type(error).__name__
            if attempt == attempts:
                break
            backoff = BACKOFF_BASE_S * 2 ** (attempt - 1) + self._jitter()
            wait = min(max(backoff, retry_after or 0.0), MAX_RETRY_WAIT_S)
            self.retries += 1
            logger.warning(
                "embedding call of %d texts failed (%s), attempt %d/%d; retrying in %.1f s",
                len(batch), reason, attempt, attempts, wait,
            )
            self._sleep(wait)
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
