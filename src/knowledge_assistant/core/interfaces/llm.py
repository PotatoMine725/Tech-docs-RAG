from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    response_schema: dict | None = None  # JSON schema; None = free text
    temperature: float = 0.0
    max_output_tokens: int = 1024


@dataclass(frozen=True)
class LLMResponse:
    """One answer and how it was obtained (ADR-0004 D12/D13 + amendment 2026-09-26).

    `retry_count` counts retries on the answer model only (0..max_attempts-1); the single fallback call is not a
    retry, it sets `fallback_used` and `model_used`. `latency_ms` is the model time of the call that produced this
    answer; time spent waiting is reported apart, so the latency report can separate the two: `retry_wait_ms` is the
    backoff between attempts, `throttle_wait_ms` the client-side per-minute throttle. Token counts are None when the
    provider did not report them.
    """

    text: str
    model_used: str
    retry_count: int
    fallback_used: bool
    prompt_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    thoughts_tokens: int | None = None
    retry_wait_ms: float = 0.0
    throttle_wait_ms: float = 0.0


class LLM(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
