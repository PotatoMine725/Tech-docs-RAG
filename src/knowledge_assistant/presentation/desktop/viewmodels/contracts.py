"""The ONLY file in presentation that knows the shape of an answer the view-model shows.

Field names copy agents/prompts/07-RAG-002 §1 (AnswerResult / Citation). Owner decision D2:
an insufficient answer may carry `missing_information` and related-only citations.
`model_used` and `fallback_used` are flattened from `AnswerResult.llm` (None / False when the retrieval gate
fired). The core result is mapped onto this shape in ONE place: `core_ask_question.py` (GUI-001).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Citation:
    marker: int
    document_name: str
    location: str  # heading path
    excerpt: str  # original English text
    source_url: str
    related_only: bool = False  # True: related content, NOT the answer (insufficient answers only)


@dataclass(frozen=True)
class AnswerResult:
    question: str
    language: str  # "en" | "vi"
    answer: str  # localized message when insufficient
    insufficient: bool
    insufficient_reason: str | None = None  # "retrieval_gate" | "llm" | None
    missing_information: str | None = None
    citations: tuple[Citation, ...] = ()
    latency_ms: dict[str, float] = field(default_factory=dict)  # ..., "total"
    model_used: str | None = None
    fallback_used: bool = False  # the answer came from the fallback model


class AskQuestionError(Exception):
    """Failure raised by the port. `kind`: quota | unavailable | no_index | other."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind


class AskQuestionPort(Protocol):
    def ask(self, question: str, arm: str) -> AnswerResult: ...
