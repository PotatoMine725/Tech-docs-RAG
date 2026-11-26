"""Desktop wiring: the ONLY presentation module that touches the composition root and infrastructure (GUI-001).

Why here: `composition.py` is the project's composition root (it names application and infrastructure classes);
the GUI process is one more entry point that needs it, exactly like `scripts/ask.py`. `wiring.py` is that entry
point's seam: view-model, view, adapter and fake stay free of infrastructure imports, and `app.py` only calls
`build_real_port()`. `tests/unit/test_project_structure.py` pins that nothing else in presentation imports
`composition` or `infrastructure`.

Providers come from configuration (EMBEDDING_PROVIDER, LLM_PROVIDER, RERANK_PROVIDER) via the composition root; this
module names no concrete provider. Shared state: ONE LLM for both arms, so the per-minute throttles are shared; ONE
reranker for both arms, so its model (about 1.6 GB, ADR-0009) loads once, on the first rerank; one `AnswerQuestion` per
arm, built on first use (the window opens even when an index is missing; the error shows on the first question). The
three providers themselves are created at start, so a bad provider setting (e.g. RERANK_PROVIDER) fails at start.
`ALLOW_FALLBACK` is forced to true here (the app answers with the fallback model when the answer model fails;
the evaluation runner does the opposite in its own process).
"""
from __future__ import annotations

import threading
from dataclasses import replace

from knowledge_assistant.application.generation.answer_question import AnswerQuestion
from knowledge_assistant.composition import (
    build_answer_service,
    create_embedder,
    create_llm,
    create_reranker,
    open_embedder,
)
from knowledge_assistant.config import get_answer_settings
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask

from .viewmodels.core_ask_question import CoreAskQuestion


class PerCallEmbedder:
    """Query embedder that opens the cached embedder for each call and closes it again.

    The embedding cache is a SQLite connection, which may only be used by the thread that created it, while the
    thread pool runs each question on whichever worker is free. Opening per call is safe on any thread and costs
    one file open (a cached query text still spends no request). The provider itself is created once and shared, so
    a local model loads once per app run; a lock keeps one query embedding at a time (the local model already uses
    every core, and the Gemini throttle is not thread-safe).
    """

    def __init__(self) -> None:
        self._inner = create_embedder()
        self._lock = threading.Lock()

    @property
    def model_id(self) -> str:
        return self._inner.model_id

    def embed(self, texts: list[str], task: EmbeddingTask) -> list[list[float]]:
        with self._lock, open_embedder(inner=self._inner) as embedder:
            return embedder.embed(texts, task)


def build_real_port() -> CoreAskQuestion:
    llm = create_llm(replace(get_answer_settings(), allow_fallback=True))
    embedder = PerCallEmbedder()
    reranker = create_reranker()  # cheap: the model loads on the first rerank, and both arms then share that one load

    def service_for_arm(arm: str) -> AnswerQuestion:
        return build_answer_service(arm, llm, embedder, reranker=reranker)

    return CoreAskQuestion(service_for_arm)
