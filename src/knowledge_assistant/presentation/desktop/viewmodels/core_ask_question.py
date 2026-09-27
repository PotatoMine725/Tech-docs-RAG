"""The ONE adapter between the core use case and the GUI contract (GUI-001; RAG-002 report, mismatches 1-7).

`to_gui_result` maps core `AnswerResult` -> `contracts.AnswerResult`; `CoreAskQuestion` is the `AskQuestionPort` the
view-model calls: it picks the per-arm `AnswerQuestion` (built lazily by an injected factory) and maps failures to
`AskQuestionError(kind)`. Imports core only: the factory is supplied by `wiring.py`.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol

from knowledge_assistant.core.exceptions import LLMError, RetrievalError, VectorStoreError
from knowledge_assistant.core.models import AnswerResult as CoreAnswerResult

from .contracts import AnswerResult, AskQuestionError, Citation


class _Service(Protocol):
    def ask(self, question: str) -> CoreAnswerResult: ...


def to_gui_result(result: CoreAnswerResult) -> AnswerResult:
    llm = result.llm  # None when the retrieval gate answered (no model call)
    return AnswerResult(
        question=result.question,
        language=result.language,
        answer=result.answer,
        insufficient=result.insufficient,
        insufficient_reason=result.insufficient_reason,
        missing_information=result.missing_information,
        citations=tuple(
            # D2: every citation of an insufficient answer is related content, not the answer (mismatch 1)
            Citation(c.marker, c.document_name, c.location, c.excerpt, c.source_url, related_only=result.insufficient)
            for c in result.citations
        ),
        latency_ms=dict(result.latency_ms),  # no "generate" key when the gate answered (mismatch 5): nothing invented
        model_used=llm.model_used if llm else None,
        fallback_used=bool(llm and llm.fallback_used),
    )


def to_gui_error(error: Exception) -> AskQuestionError:
    """LLMError.kind is the GUI kind 1:1; a missing/empty index is no_index; everything else is other."""
    if isinstance(error, LLMError):
        kind = error.kind
    elif isinstance(error, (RetrievalError, VectorStoreError)):
        kind = "no_index"
    else:
        kind = "other"
    return AskQuestionError(kind, str(error))


class CoreAskQuestion:
    def __init__(self, service_for_arm: Callable[[str], _Service]) -> None:
        self._factory = service_for_arm
        self._services: dict[str, _Service] = {}
        self._lock = threading.Lock()

    def _service(self, arm: str) -> _Service:
        with self._lock:  # built on the worker thread on first use; never twice
            if arm not in self._services:
                self._services[arm] = self._factory(arm)
            return self._services[arm]

    def ask(self, question: str, arm: str) -> AnswerResult:
        try:
            return to_gui_result(self._service(arm).ask(question))
        except AskQuestionError:
            raise
        except Exception as error:
            raise to_gui_error(error) from error
