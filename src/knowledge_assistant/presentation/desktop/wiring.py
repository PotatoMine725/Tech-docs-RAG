"""Desktop wiring: the ONLY presentation module that touches the composition root and infrastructure (GUI-001).

Why here: `composition.py` is the project's composition root (it names application and infrastructure classes);
the GUI process is one more entry point that needs it, exactly like `scripts/ask.py`. `wiring.py` is that entry
point's seam: view-model, view, adapter and fake stay free of infrastructure imports, and `app.py` only calls
`build_real_port()`. `tests/unit/test_project_structure.py` pins that nothing else in presentation imports
`composition` or `infrastructure`.

Shared state: ONE `GeminiLLM` for both arms, so the per-minute throttles are shared; one `AnswerQuestion` per arm,
built on first use (the window opens even when an index is missing; the error shows on the first question).
`ALLOW_FALLBACK` is forced to true here (the app answers with the fallback model when the answer model fails;
the evaluation runner does the opposite in its own process).
"""
from __future__ import annotations

from dataclasses import replace

from knowledge_assistant.application.generation.answer_question import AnswerQuestion
from knowledge_assistant.composition import build_answer_service, open_embedder
from knowledge_assistant.config import get_answer_settings, get_embedding_settings
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.llm.gemini import GeminiLLM

from .viewmodels.core_ask_question import CoreAskQuestion


class PerCallEmbedder:
    """Query embedder that opens the cached embedder for each call and closes it again.

    The embedding cache is a SQLite connection, which may only be used by the thread that created it, while the
    thread pool runs each question on whichever worker is free. Opening per call is safe on any thread and costs
    one file open (a cached query text still spends no request).
    """

    @property
    def model_id(self) -> str:
        return get_embedding_settings().model_id

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        with open_embedder() as embedder:
            return embedder.embed(texts, task)


def build_real_port() -> CoreAskQuestion:
    llm = GeminiLLM(replace(get_answer_settings(), allow_fallback=True))
    embedder = PerCallEmbedder()

    def service_for_arm(arm: str) -> AnswerQuestion:
        return build_answer_service(arm, llm, embedder)

    return CoreAskQuestion(service_for_arm)
