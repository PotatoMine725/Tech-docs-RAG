"""Gemini adapter for core.interfaces.llm (RAG-002: basic, one model, no retry; RAG-003 adds retry/fallback).

JSON mode uses the installed google-genai 1.75.0 API: `response_mime_type="application/json"` plus
`response_json_schema` (a plain JSON-schema dict; `response_schema` would take the OpenAPI subset instead).
Provider errors (e.g. HTTP 429/503 `errors.APIError`) are not caught here yet: they reach the caller unchanged.
"""
import time
from collections.abc import Callable
from typing import Any

from google import genai
from google.genai import types

from knowledge_assistant.config import AnswerSettings, get_answer_settings, get_gemini_api_key
from knowledge_assistant.core.exceptions import ConfigurationError, GenerationError
from knowledge_assistant.core.interfaces.llm import LLMRequest, LLMResponse

UNUSABLE_FINISH = {"MAX_TOKENS", "SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}


def _finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None) or []
    reason = getattr(candidates[0], "finish_reason", None) if candidates else None
    return getattr(reason, "name", None) or (str(reason) if reason is not None else None)


class GeminiLLM:
    def __init__(
        self,
        settings: AnswerSettings | None = None,
        client: Any = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._settings = settings or get_answer_settings()
        self._client = client
        self._clock = clock
        self.requests = 0  # HTTP calls made (quota accounting for scripts)
        self.last_usage: dict[str, int | None] = {}  # token counts of the last call, incl. thinking tokens
        self.last_finish_reason: str | None = None

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
        start = self._clock()
        self.requests += 1
        response = client.models.generate_content(model=self._settings.model, contents=request.prompt, config=config)
        latency_ms = (self._clock() - start) * 1000.0

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
                f"generation stopped early (finish_reason={self.last_finish_reason}, usage={self.last_usage})",
                raw_text=text,
            )
        if not text:
            raise GenerationError(f"empty response (finish_reason={self.last_finish_reason})", raw_text=text)
        return LLMResponse(
            text=text,
            model_used=self._settings.model,
            retry_count=0,
            fallback_used=False,
            prompt_tokens=self.last_usage["prompt_tokens"],
            output_tokens=self.last_usage["output_tokens"],
            latency_ms=latency_ms,
        )
