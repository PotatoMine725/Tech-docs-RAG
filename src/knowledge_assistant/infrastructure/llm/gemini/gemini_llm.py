"""Gemini adapter for core.interfaces.llm (RAG-003: throttle, retry, fallback, error classification, accounting).

JSON mode uses the installed google-genai 1.75.0 API: `response_mime_type="application/json"` plus
`response_json_schema` (a plain JSON-schema dict; `response_schema` would take the OpenAPI subset instead).

Policy (ADR-0004 amendment 2026-09-26, OD-11):
  - The answer model gets up to `max_attempts` (3) attempts on a per-minute 429, 5xx, timeout or connection error,
    with exponential backoff, jitter and the server's retry-after; one wait never exceeds 120 s.
  - Then the fallback model gets ONE attempt (only when ALLOW_FALLBACK is true). A daily-quota 429 skips the retries
    and goes straight to that single fallback attempt. Errors that no retry can fix (400, 401, 403, 404, ...) are
    raised at once, without the fallback.
  - Each model has its own per-minute throttle (config); every attempt, retries and fallback included, passes it.
  - No google.genai / httpx exception leaves this module: provider failures become core LLMError subtypes whose
    `kind` (quota | unavailable | other) is the GUI's AskQuestionError kind. When both models fail, the error
    describes the answer model's failure and mentions the fallback's. Unusable model output stays a GenerationError
    (not retried, no fallback).
The SDK's own retry is left off (`retry_options` unset = one attempt), so attempts are counted here and only here.
"""
import logging
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types

from knowledge_assistant.config import AnswerSettings, get_answer_settings, get_gemini_api_key
from knowledge_assistant.core.exceptions import (
    ConfigurationError,
    GenerationError,
    LLMError,
    LLMQuotaError,
    LLMRequestError,
    LLMUnavailableError,
)
from knowledge_assistant.core.interfaces.llm import LLMRequest, LLMResponse
from knowledge_assistant.infrastructure.embeddings.throttle import SlidingWindowThrottle
from knowledge_assistant.infrastructure.gemini_retry import (
    DAILY_RESET,
    PROVIDER_ERRORS,
    Failure,
    backoff_wait_s,
    classify_failure,
    redact_key,
)

UNUSABLE_FINISH = {"MAX_TOKENS", "SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}

logger = logging.getLogger(__name__)


def _finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    return getattr(reason, "name", None) or (str(reason) if reason is not None else None)


def build_throttles(
    settings: AnswerSettings,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, SlidingWindowThrottle]:
    """One per-minute request throttle per model, at the configured throttle RPM (below the provider's RPM).

    Requests only: TPM is not enforced client-side (see ModelLimits). One GeminiLLM instance shares its throttles
    across its calls; two instances of the same model each get their own window.
    """
    throttles = {
        settings.model: SlidingWindowThrottle(settings.limits.throttle_rpm, settings.limits.tpm, clock=clock, sleep=sleep)
    }
    if settings.fallback_model not in throttles:
        throttles[settings.fallback_model] = SlidingWindowThrottle(
            settings.fallback_limits.throttle_rpm, settings.fallback_limits.tpm, clock=clock, sleep=sleep
        )
    return throttles


@dataclass
class _Tally:
    """What one generate() call spent besides model time."""

    retries: int = 0
    retry_wait_s: float = 0.0
    throttle_wait_s: float = 0.0


@dataclass
class _Attempt:
    response: Any = None
    latency_ms: float = 0.0
    failure: Failure | None = None
    error: Exception | None = None  # the raw provider exception behind `failure`


class GeminiLLM:
    def __init__(
        self,
        settings: AnswerSettings | None = None,
        client: Any = None,
        clock: Callable[[], float] = time.perf_counter,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
        throttles: Mapping[str, SlidingWindowThrottle] | None = None,
    ) -> None:
        self._settings = settings or get_answer_settings()
        self._client = client
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        self._throttles = dict(throttles) if throttles is not None else build_throttles(self._settings)
        self.requests = 0  # HTTP calls made, retries and fallback included (quota accounting for scripts)
        self.requests_by_model: dict[str, int] = {}
        self.last_usage: dict[str, int | None] = {}  # token counts of the last answer, incl. thinking tokens
        self.last_finish_reason: str | None = None
        self._logged_first_429 = False  # the first 429's raw body is logged once per instance

    @property
    def model(self) -> str:
        return self._settings.model

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

    def generate(self, request: LLMRequest) -> LLMResponse:
        client = self._get_client()
        options: dict[str, Any] = {"temperature": request.temperature, "max_output_tokens": request.max_output_tokens}
        if request.response_schema is not None:
            options.update(response_mime_type="application/json", response_json_schema=request.response_schema)
        config = types.GenerateContentConfig(**options)
        settings = self._settings
        tally = _Tally()

        failed: _Attempt | None = None
        for attempt in range(1, settings.max_attempts + 1):
            outcome = self._attempt(client, settings.model, request, config, tally)
            if outcome.failure is None:
                return self._response(outcome, settings.model, tally, fallback_used=False)
            failed = outcome
            if not outcome.failure.retryable or attempt == settings.max_attempts:
                break
            wait = backoff_wait_s(attempt, outcome.failure.retry_after_s, self._jitter())
            tally.retries += 1
            tally.retry_wait_s += wait
            logger.warning(
                "%s call failed (%s), attempt %d/%d; retrying in %.1f s",
                settings.model, outcome.failure.reason, attempt, settings.max_attempts, wait,
            )
            self._sleep(wait)

        fallback_failed: _Attempt | None = None
        if failed.failure.kind != "other" and settings.allow_fallback and settings.fallback_model != settings.model:
            logger.warning(
                "%s failed (%s); one attempt on the fallback model %s",
                settings.model, failed.failure.reason, settings.fallback_model,
            )
            outcome = self._attempt(client, settings.fallback_model, request, config, tally)
            if outcome.failure is None:
                return self._response(outcome, settings.fallback_model, tally, fallback_used=True)
            fallback_failed = outcome
        raise self._error(failed, fallback_failed, tally)

    def _attempt(self, client: Any, model: str, request: LLMRequest, config: Any, tally: _Tally) -> _Attempt:
        tally.throttle_wait_s += self._throttles[model].acquire(0)
        self.requests += 1
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        start = self._clock()
        try:
            response = client.models.generate_content(model=model, contents=request.prompt, config=config)
        except PROVIDER_ERRORS as error:
            failure = classify_failure(error)
            if failure.status == 429 and not self._logged_first_429:
                self._logged_first_429 = True
                logger.warning("first HTTP 429 of this run (model %s), raw error body: %s", model, failure.body)
            return _Attempt(failure=failure, error=error)
        return _Attempt(response=response, latency_ms=(self._clock() - start) * 1000.0)

    def _response(self, outcome: _Attempt, model: str, tally: _Tally, fallback_used: bool) -> LLMResponse:
        response = outcome.response
        usage = getattr(response, "usage_metadata", None)
        self.last_usage = {
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "output_tokens": getattr(usage, "candidates_token_count", None),
            "thoughts_tokens": getattr(usage, "thoughts_token_count", None),
        }
        self.last_finish_reason = _finish_reason(response)
        text = getattr(response, "text", None)
        if self.last_finish_reason in UNUSABLE_FINISH:
            raise GenerationError(
                f"generation stopped early (model={model}, finish_reason={self.last_finish_reason}, "
                f"usage={self.last_usage})",
                raw_text=text,
            )
        if not text:
            raise GenerationError(
                f"empty response (model={model}, finish_reason={self.last_finish_reason})", raw_text=text
            )
        return LLMResponse(
            text=text,
            model_used=model,
            retry_count=tally.retries,
            fallback_used=fallback_used,
            prompt_tokens=self.last_usage["prompt_tokens"],
            output_tokens=self.last_usage["output_tokens"],
            latency_ms=outcome.latency_ms,
            thoughts_tokens=self.last_usage["thoughts_tokens"],
            retry_wait_ms=tally.retry_wait_s * 1000.0,
            throttle_wait_ms=tally.throttle_wait_s * 1000.0,
        )

    def _error(self, failed: _Attempt, fallback_failed: _Attempt | None, tally: _Tally) -> LLMError:
        """The answer model's failure as a core error (the caller raises it), with the fallback's outcome told."""
        settings = self._settings
        failure = failed.failure
        attempts = tally.retries + 1
        if failure.kind == "quota":
            what = (
                f"daily quota exhausted ({failure.daily_quota_id}); resume after the {DAILY_RESET} reset"
                if failure.daily_quota_id
                else f"rate limit ({failure.reason}) persisted through {attempts} attempt(s)"
            )
        elif failure.kind == "unavailable":
            what = f"service unavailable ({failure.reason}) after {attempts} attempt(s)"
        else:
            what = f"request failed ({failure.reason})"
        message = f"{settings.model}: {what}"
        if fallback_failed is not None:
            message += f"; the fallback model {settings.fallback_model} also failed ({fallback_failed.failure.reason})"
        elif failure.kind != "other" and not settings.allow_fallback:
            message += "; the fallback model is off (ALLOW_FALLBACK=false)"
        details = dict(
            model=settings.model,
            retry_count=tally.retries,
            fallback_attempted=fallback_failed is not None,
            provider_body=failure.body,
        )
        message = redact_key(message)
        if failure.kind == "quota":
            error: LLMError = LLMQuotaError(message, daily=failure.daily_quota_id is not None, **details)
        elif failure.kind == "unavailable":
            error = LLMUnavailableError(message, **details)
        else:
            error = LLMRequestError(message, **details)
        error.__cause__ = failed.error
        return error
