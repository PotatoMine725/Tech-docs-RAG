"""Gemini adapter for core.interfaces.llm. Model name is TBD; no calls are made at setup."""
from knowledge_assistant.config import get_gemini_api_key
from knowledge_assistant.core.exceptions import ConfigurationError


class GeminiLLM:
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or get_gemini_api_key()

    def generate(self, prompt: str) -> str:
        if not self._api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set")
        raise NotImplementedError("Generation is implemented in the RAG phase")
