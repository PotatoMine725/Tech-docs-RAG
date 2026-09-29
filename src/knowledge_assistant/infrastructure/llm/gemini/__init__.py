"""Gemini adapter for core.interfaces.llm; the model name comes from configuration (`ANSWER_MODEL`)."""
from knowledge_assistant.infrastructure.llm.gemini.gemini_llm import GeminiLLM

__all__ = ["GeminiLLM"]
