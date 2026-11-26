"""LlamaCppLLM with a fake transport: request shape, reply parsing, error mapping. No server, no network."""
import json

import pytest

from knowledge_assistant.config import LlamaCppSettings, get_llamacpp_settings
from knowledge_assistant.core.exceptions import ConfigurationError, LLMRequestError, LLMUnavailableError
from knowledge_assistant.core.interfaces.llm import LLMRequest
from knowledge_assistant.infrastructure.llm.llamacpp import LlamaCppLLM

SETTINGS = LlamaCppSettings(base_url="http://127.0.0.1:8080", model="qwen3.5-2b-q4_k_m", timeout_s=30,
                            max_output_tokens=512, seed=42, chat_template_kwargs={"enable_thinking": False},
                            system_prompt=None)


def _reply(content="Answer [1].", **extra):
    return json.dumps({"model": "qwen3.5-2b-q4_k_m", "choices": [{"message": {"content": content},
                                                                    "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": 900, "completion_tokens": 40},
                       "timings": {"prompt_ms": 7300.5, "predicted_ms": 3100.0}, **extra}).encode()


class Transport:
    def __init__(self, status=200, body=b"", error=None):
        self.status, self.body, self.error, self.calls = status, body, error, []

    def __call__(self, url, body, timeout_s):
        self.calls.append((url, json.loads(body), timeout_s))
        if self.error:
            raise self.error
        return self.status, self.body


def _llm(transport, settings=SETTINGS):
    ticks = iter([0.0, 2.5])
    return LlamaCppLLM(settings, transport=transport, clock=lambda: next(ticks))


def test_request_shape_text_mode():
    transport = Transport(body=_reply())
    response = _llm(transport).generate(LLMRequest("PROMPT", max_output_tokens=1024))
    [(url, body, timeout)] = transport.calls
    assert url == "http://127.0.0.1:8080/v1/chat/completions" and timeout == 30
    assert body["messages"] == [{"role": "user", "content": "PROMPT"}]
    assert body["max_tokens"] == 512  # capped by the local setting
    assert body["temperature"] == 0.0 and body["seed"] == 42 and body["stream"] is False
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert "response_format" not in body
    assert response.text == "Answer [1]." and response.model_used == "qwen3.5-2b-q4_k_m"
    assert (response.prompt_tokens, response.output_tokens) == (900, 40)
    assert response.latency_ms == 2500.0 and response.time_to_first_token_ms == 7300.5
    assert not response.fallback_used and response.retry_count == 0


def test_schema_is_sent_as_json_schema_response_format_and_system_line_first():
    settings = LlamaCppSettings(**{**SETTINGS.__dict__, "system_prompt": "/no_think", "chat_template_kwargs": {}})
    transport = Transport(body=_reply('{"a": 1}'))
    _llm(transport, settings).generate(LLMRequest("P", response_schema={"type": "object"}))
    body = transport.calls[0][1]
    assert body["response_format"] == {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}}
    assert body["messages"][0] == {"role": "system", "content": "/no_think"}
    assert "chat_template_kwargs" not in body


def test_leading_think_block_is_removed():
    response = _llm(Transport(body=_reply("<think>\nhmm\n</think>\n\nReal answer [2]."))).generate(LLMRequest("P"))
    assert response.text == "Real answer [2]."


def test_missing_timings_give_unknown_ttft():
    body = json.dumps({"choices": [{"message": {"content": "x"}}]}).encode()
    response = _llm(Transport(body=body)).generate(LLMRequest("P"))
    assert response.time_to_first_token_ms is None and response.prompt_tokens is None


@pytest.mark.parametrize(("transport", "error"), [
    (Transport(error=ConnectionRefusedError("refused")), LLMUnavailableError),
    (Transport(error=TimeoutError("timed out")), LLMUnavailableError),
    (Transport(status=503, body=b"loading model"), LLMUnavailableError),
    (Transport(status=400, body=b"bad request"), LLMRequestError),
    (Transport(body=b"not json"), LLMRequestError),
    (Transport(body=b'{"choices": []}'), LLMRequestError),
])
def test_failures_map_to_core_errors_without_retry(transport, error):
    llm = _llm(transport)
    with pytest.raises(error) as caught:
        llm.generate(LLMRequest("P"))
    assert caught.value.model == "qwen3.5-2b-q4_k_m" and caught.value.retry_count == 0
    assert llm.requests == 1 == len(transport.calls)


def test_settings_need_a_model_id_and_valid_kwargs(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_MODEL", raising=False)
    with pytest.raises(ConfigurationError, match="LOCAL_LLM_MODEL"):
        get_llamacpp_settings()
    monkeypatch.setenv("LOCAL_LLM_MODEL", "m")
    monkeypatch.setenv("LOCAL_LLM_CHAT_TEMPLATE_KWARGS", "[1]")
    with pytest.raises(ConfigurationError, match="JSON object"):
        get_llamacpp_settings()
    monkeypatch.delenv("LOCAL_LLM_CHAT_TEMPLATE_KWARGS")
    monkeypatch.setenv("LLAMACPP_URL", "http://localhost:9000/")
    settings = get_llamacpp_settings()
    assert settings.base_url == "http://localhost:9000" and settings.chat_template_kwargs == {"enable_thinking": False}
