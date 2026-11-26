"""Local answer model through `llama-server` (llama.cpp), its OpenAI-style `/v1/chat/completions` endpoint.

Standard library HTTP only (no new dependency). The server is started outside the app for now (the evaluation and the
benchmark start it themselves); starting and stopping it from the app is a later step of the plan (§9).

- `response_schema` set: sent as `response_format: json_schema`, which `llama-server` enforces with a grammar.
- Thinking: `chat_template_kwargs` (default `{"enable_thinking": false}`) and an optional system line come from
  configuration. A leading `<think>...</think>` block that still reaches the content is removed from the answer.
- Failures map to the core LLM errors: no server / timeout / 5xx -> LLMUnavailableError, any other HTTP error or an
  unreadable reply -> LLMRequestError. No retries, no fallback.
- `time_to_first_token_ms` is the server's own prompt-processing time (`timings.prompt_ms`), the cost a streamed
  answer would wait before its first word; None when the server does not report it.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from knowledge_assistant.config import LlamaCppSettings, get_llamacpp_settings
from knowledge_assistant.core.exceptions import LLMRequestError, LLMUnavailableError
from knowledge_assistant.core.interfaces.llm import LLMRequest, LLMResponse

_THINK_BLOCK = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL)

Transport = Callable[[str, bytes, float], tuple[int, bytes]]


def urllib_transport(url: str, body: bytes, timeout_s: float) -> tuple[int, bytes]:
    """POST `body` as JSON; (HTTP status, response body). Connection failures and timeouts raise OSError."""
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def strip_think(text: str) -> str:
    return _THINK_BLOCK.sub("", text, count=1)


class LlamaCppLLM:
    def __init__(
        self,
        settings: LlamaCppSettings | None = None,
        transport: Transport = urllib_transport,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._settings = settings or get_llamacpp_settings()
        self._transport = transport
        self._clock = clock
        self.requests = 0  # HTTP calls made (same accounting attributes as GeminiLLM)
        self.requests_by_model: dict[str, int] = {}
        self.last_timings: dict[str, Any] = {}
        self.last_finish_reason: str | None = None

    @property
    def model(self) -> str:
        return self._settings.model

    def payload(self, request: LLMRequest) -> dict:
        settings = self._settings
        messages = []
        if settings.system_prompt:
            messages.append({"role": "system", "content": settings.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        body: dict[str, Any] = {
            "model": settings.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": min(request.max_output_tokens, settings.max_output_tokens),
            "seed": settings.seed,
            "stream": False,
            "cache_prompt": True,  # fixed instructions first in the prompt, so the server reuses that prefix
        }
        if settings.chat_template_kwargs:
            body["chat_template_kwargs"] = settings.chat_template_kwargs
        if request.response_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": {"schema": request.response_schema}}
        return body

    def generate(self, request: LLMRequest) -> LLMResponse:
        model = self._settings.model
        url = f"{self._settings.base_url}/v1/chat/completions"
        details = {"model": model, "retry_count": 0, "fallback_attempted": False}
        self.requests += 1
        self.requests_by_model[model] = self.requests_by_model.get(model, 0) + 1
        start = self._clock()
        try:
            status, raw = self._transport(url, json.dumps(self.payload(request)).encode("utf-8"),
                                          self._settings.timeout_s)
        except OSError as error:  # refused, reset, DNS, timeout (TimeoutError and URLError are OSError)
            raise LLMUnavailableError(f"llama-server at {self._settings.base_url} is not reachable: {error}",
                                      **details) from error
        latency_ms = (self._clock() - start) * 1000.0
        body_text = raw.decode("utf-8", "replace")
        if status >= 500:
            raise LLMUnavailableError(f"llama-server returned HTTP {status}", provider_body=body_text, **details)
        if status != 200:
            raise LLMRequestError(f"llama-server returned HTTP {status}", provider_body=body_text, **details)
        try:
            data = json.loads(body_text)
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("message.content is not a string")
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise LLMRequestError(f"llama-server reply is not a chat completion: {error}", provider_body=body_text,
                                  **details) from error
        usage = data.get("usage") or {}
        self.last_timings = data.get("timings") or {}
        self.last_finish_reason = choice.get("finish_reason")
        prompt_ms = self.last_timings.get("prompt_ms")
        return LLMResponse(
            text=strip_think(content),
            model_used=model,
            retry_count=0,
            fallback_used=False,
            prompt_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            time_to_first_token_ms=float(prompt_ms) if isinstance(prompt_ms, (int, float)) else None,
        )
