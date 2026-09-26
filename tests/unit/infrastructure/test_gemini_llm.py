"""GeminiLLM with a fake client: request shape (JSON mode), token counts, latency, early-stop errors. No network."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from knowledge_assistant.config import get_answer_settings
from knowledge_assistant.core.exceptions import GenerationError
from knowledge_assistant.core.interfaces.llm import LLMRequest
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM


class FakeGenerateModels:
    def __init__(self, text='{"ok": true}', finish="STOP"):
        self.text = text
        self.finish = finish
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        return SimpleNamespace(
            text=self.text,
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=self.finish))],
            usage_metadata=SimpleNamespace(prompt_token_count=120, candidates_token_count=30, thoughts_token_count=5),
        )


def _llm(models, model="pinned-test-model"):
    ticks = iter([1.0, 1.25])
    settings = replace(get_answer_settings(), model=model)
    return GeminiLLM(settings, client=SimpleNamespace(models=models), clock=lambda: next(ticks))


def test_json_mode_request_and_response_fields():
    models = FakeGenerateModels()
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    response = _llm(models).generate(LLMRequest("PROMPT", response_schema=schema, max_output_tokens=512))
    [call] = models.calls
    assert call["model"] == "pinned-test-model" and call["contents"] == "PROMPT"
    assert call["config"].response_mime_type == "application/json"
    assert call["config"].response_json_schema == schema
    assert call["config"].temperature == 0.0 and call["config"].max_output_tokens == 512
    assert response.text == '{"ok": true}'
    assert (response.model_used, response.retry_count, response.fallback_used) == ("pinned-test-model", 0, False)
    assert (response.prompt_tokens, response.output_tokens, response.thoughts_tokens) == (120, 30, 5)
    assert response.latency_ms == pytest.approx(250.0)


def test_free_text_request_has_no_json_mode():
    models = FakeGenerateModels(text="plain")
    _llm(models).generate(LLMRequest("PROMPT"))
    assert models.calls[0]["config"].response_mime_type is None


@pytest.mark.parametrize(("text", "finish"), [('{"answer": "cut', "MAX_TOKENS"), (None, "STOP"), ("", "STOP")])
def test_truncated_or_empty_output_raises_generation_error(text, finish):
    with pytest.raises(GenerationError):
        _llm(FakeGenerateModels(text=text, finish=finish)).generate(LLMRequest("PROMPT"))


def test_answer_model_is_pinned_in_configuration(monkeypatch):
    monkeypatch.delenv("ANSWER_MODEL", raising=False)
    model = get_answer_settings().model
    assert model == "gemini-3.5-flash-lite" and "latest" not in model
