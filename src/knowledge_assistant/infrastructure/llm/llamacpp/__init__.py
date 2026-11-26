"""llama.cpp (`llama-server`) adapter for core.interfaces.llm; the model id comes from configuration (`LOCAL_LLM_MODEL`)."""
from knowledge_assistant.infrastructure.llm.llamacpp.llamacpp_llm import LlamaCppLLM

__all__ = ["LlamaCppLLM"]
