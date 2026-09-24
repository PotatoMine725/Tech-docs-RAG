import pytest

from knowledge_assistant.core.exceptions import ConfigurationError
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM


def test_gemini_requires_api_key_and_makes_no_call(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        GeminiLLM().generate("hi")
