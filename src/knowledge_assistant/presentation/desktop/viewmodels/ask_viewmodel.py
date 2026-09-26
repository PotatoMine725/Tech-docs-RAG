"""View-model for the question/answer window. Plain Python: no Qt import, so it tests without an event loop.

The port call runs through an injected `executor(fn, on_ok, on_err)`: the Qt app supplies a thread-pool one
(callbacks arrive on the GUI thread), tests supply a synchronous one.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable

from .contracts import AnswerResult, AskQuestionError, AskQuestionPort, Citation

Executor = Callable[[Callable[[], object], Callable[[object], None], Callable[[Exception], None]], None]

ARMS = ("A", "B")

_ERROR_TEXT = {
    "quota": "The Gemini quota is used up for now. Wait a few minutes and ask again.",
    "unavailable": "The model service is temporarily unavailable (503). Try again in a moment.",
    "no_index": "The search index was not found. Build the index first, then ask again.",
}


_ERROR_TITLE = {
    "quota": "Quota used up",
    "unavailable": "Model service unavailable",
    "no_index": "Search index not found",
}


class ViewState(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ANSWER = "answer"
    INSUFFICIENT = "insufficient"
    ERROR = "error"


class AskViewModel:
    def __init__(self, port: AskQuestionPort, executor: Executor) -> None:
        self._port = port
        self._executor = executor
        self._listeners: list[Callable[[], None]] = []
        self.state = ViewState.IDLE
        self.arm = ARMS[0]
        self.result: AnswerResult | None = None
        self.error_title = ""
        self.error_message = ""
        self.selected: Citation | None = None

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()

    # ---- commands -------------------------------------------------------
    def set_arm(self, arm: str) -> None:
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        self.arm = arm

    def can_submit(self, question: str) -> bool:
        return bool(question.strip()) and self.state is not ViewState.BUSY

    def submit(self, question: str) -> None:
        if not self.can_submit(question):
            return
        question = question.strip()
        arm = self.arm
        self.state = ViewState.BUSY
        self.result, self.selected, self.error_message = None, None, ""
        self._notify()
        self._executor(lambda: self._port.ask(question, arm), self._on_ok, self._on_err)

    def select_citation(self, index: int) -> None:
        if self.result and 0 <= index < len(self.result.citations):
            self.selected = self.result.citations[index]
            self._notify()

    # ---- executor callbacks (GUI thread) --------------------------------
    def _on_ok(self, result: object) -> None:
        assert isinstance(result, AnswerResult)
        self.result = result
        self.state = ViewState.INSUFFICIENT if result.insufficient else ViewState.ANSWER
        self._notify()

    def _on_err(self, exc: Exception) -> None:
        kind = exc.kind if isinstance(exc, AskQuestionError) else "other"
        self.error_title = _ERROR_TITLE.get(kind, "Could not get an answer")
        self.error_message = _ERROR_TEXT.get(kind) or f"Something went wrong: {exc}"
        self.state = ViewState.ERROR
        self._notify()

    # ---- derived text for the view --------------------------------------
    @property
    def status_line(self) -> str:
        if self.state is ViewState.BUSY:
            return "Working…"
        if not self.result:
            return ""
        total = self.result.latency_ms.get("total")
        parts = []
        if total is not None:
            parts.append(f"Total latency {total / 1000:.1f} s")
        parts.append(f"model: {self.result.model_used or 'none (no model call)'}")
        return " · ".join(parts)

    @property
    def can_copy(self) -> bool:
        return self.state is ViewState.ANSWER

    @property
    def copy_text(self) -> str:
        return self.result.answer if self.can_copy and self.result else ""
