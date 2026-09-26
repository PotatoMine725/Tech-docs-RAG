import pytest

from knowledge_assistant.core.exceptions import ConfigurationError
from knowledge_assistant.core.interfaces.llm import LLMRequest
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM


def test_gemini_requires_api_key_and_makes_no_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    llm = GeminiLLM()
    with pytest.raises(ConfigurationError):
        llm.generate(LLMRequest("hi"))
    assert llm.requests == 0
