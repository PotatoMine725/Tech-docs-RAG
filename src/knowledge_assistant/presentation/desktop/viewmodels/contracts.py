# mirror of AnswerResult (prompt 07 §1) — reconcile in GUI-001
"""The ONLY file in presentation that knows the shape of an answer.

Field names copy agents/prompts/07-RAG-002 §1 (AnswerResult / Citation). Owner decision D2:
an insufficient answer may carry `missing_information` and related-only citations.
`model_used` is flattened from `AnswerResult.llm.model_used` (None when the retrieval gate fired).
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


class AskQuestionError(Exception):
    """Failure raised by the port. `kind`: quota | unavailable | no_index | other."""

    def __init__(self, kind: str, message: str = "") -> None:
        super().__init__(message or kind)
        self.kind = kind


class AskQuestionPort(Protocol):
    def ask(self, question: str, arm: str) -> AnswerResult: ...
