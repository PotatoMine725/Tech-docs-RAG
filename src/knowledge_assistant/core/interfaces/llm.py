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
    text: str
    model_used: str
    retry_count: int
    fallback_used: bool
    prompt_tokens: int | None
    output_tokens: int | None
    latency_ms: float


class LLM(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
