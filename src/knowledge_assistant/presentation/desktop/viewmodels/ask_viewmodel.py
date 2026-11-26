"""View-model for the notebook window. Plain Python: no Qt import, so it tests without an event loop.

The window is a conversation (a list of turns), a source list and a source viewer. Every decision lives here; the
window only formats what these properties return. The port call runs through an injected
`executor(fn, on_ok, on_err)`: the Qt app supplies a thread-pool one (callbacks arrive on the GUI thread), tests
supply a synchronous one.

The single-answer properties of the first version (`state`, `result`, `error_*`, `selected`, `status_line`,
`copy_text`) still describe the newest turn.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from knowledge_assistant.application.citation.citations import marker_spans

from .contracts import AnswerResult, AskQuestionError, AskQuestionPort, Citation

Executor = Callable[[Callable[[], object], Callable[[object], None], Callable[[Exception], None]], None]

ARMS = ("A", "B")

_SAFE_URL_SCHEMES = ("https://", "http://")

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


@dataclass
class Turn:
    """One question in the conversation and what came back for it."""

    question: str
    arm: str
    state: ViewState = ViewState.BUSY
    result: AnswerResult | None = None
    error_title: str = ""
    error_message: str = ""

    @property
    def citations(self) -> tuple[Citation, ...]:
        if self.result and self.state in (ViewState.ANSWER, ViewState.INSUFFICIENT):
            return self.result.citations
        return ()


@dataclass(frozen=True)
class Segment:
    """A piece of an answer: plain text, or a citation marker that exists in the turn's citations."""

    text: str
    marker: int | None = None


class AskViewModel:
    def __init__(self, port: AskQuestionPort, executor: Executor, sources: Sequence[str] = ()) -> None:
        self._port = port
        self._executor = executor
        self._listeners: list[Callable[[], None]] = []
        self.sources: tuple[str, ...] = tuple(sources)
        self.arm = ARMS[0]
        self.turns: list[Turn] = []
        self.last_question = ""
        self._viewer: tuple[int, int] | None = None  # (turn index, citation index) shown in the source viewer

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        for listener in self._listeners:
            listener()

    # ---- the newest turn (first-version API) ----------------------------
    @property
    def _current(self) -> Turn | None:
        return self.turns[-1] if self.turns else None

    @property
    def state(self) -> ViewState:
        return self._current.state if self._current else ViewState.IDLE

    @property
    def result(self) -> AnswerResult | None:
        return self._current.result if self._current else None

    @property
    def error_title(self) -> str:
        return self._current.error_title if self._current else ""

    @property
    def error_message(self) -> str:
        return self._current.error_message if self._current else ""

    @property
    def busy(self) -> bool:
        return any(t.state is ViewState.BUSY for t in self.turns)

    # ---- commands -------------------------------------------------------
    def set_arm(self, arm: str) -> None:
        if arm not in ARMS:
            raise ValueError(f"unknown arm {arm!r}")
        self.arm = arm

    def can_submit(self, question: str) -> bool:
        return bool(question.strip()) and not self.busy

    def submit(self, question: str) -> bool:
        """Ask a question. Returns False (and changes nothing) for a blank question or while one is being answered."""
        if not self.can_submit(question):
            return False
        self._ask(Turn(question.strip(), self.arm))
        return True

    def retry(self, index: int) -> bool:
        """Ask a finished turn's question again: it moves to the end of the conversation and is asked afresh."""
        if self.busy or not 0 <= index < len(self.turns):
            return False
        old = self.turns.pop(index)
        self._ask(Turn(old.question, old.arm))
        return True

    def _ask(self, turn: Turn) -> None:
        self.turns.append(turn)
        self.last_question = turn.question
        self._viewer = None
        self._notify()
        question, arm = turn.question, turn.arm
        try:
            self._executor(lambda: self._port.ask(question, arm),
                           lambda result: self._on_ok(turn, result), lambda exc: self._on_err(turn, exc))
        except Exception as exc:  # noqa: BLE001 - the job never started: the turn must not stay busy
            self._on_err(turn, exc)

    # ---- source viewer --------------------------------------------------
    def open_citation(self, turn_index: int, marker: int) -> bool:
        if not 0 <= turn_index < len(self.turns):
            return False
        for i, c in enumerate(self.turns[turn_index].citations):
            if c.marker == marker:
                self._viewer = (turn_index, i)
                self._notify()
                return True
        return False

    def select_citation(self, index: int) -> None:
        """Open the newest turn's citation at list position `index` (first-version API)."""
        if self.turns and 0 <= index < len(self._current.citations):
            self._viewer = (len(self.turns) - 1, index)
            self._notify()

    def step_citation(self, delta: int) -> None:
        if self._viewer is None:
            return
        t, i = self._viewer
        j = i + delta
        if 0 <= j < len(self.turns[t].citations):
            self._viewer = (t, j)
            self._notify()

    def close_viewer(self) -> None:
        if self._viewer is not None:
            self._viewer = None
            self._notify()

    @property
    def viewer_turn(self) -> int | None:
        return self._viewer[0] if self._viewer else None

    @property
    def selected(self) -> Citation | None:
        if self._viewer is None:
            return None
        t, i = self._viewer
        return self.turns[t].citations[i]

    @property
    def selected_link(self) -> str:
        """The open citation's source URL when it is a web address; empty otherwise, so nothing else is clickable."""
        url = self.selected.source_url.strip() if self.selected else ""
        return url if url.lower().startswith(_SAFE_URL_SCHEMES) else ""

    @property
    def viewer_position(self) -> str:
        if self._viewer is None:
            return ""
        t, i = self._viewer
        return f"{i + 1} of {len(self.turns[t].citations)}"

    @property
    def can_step_back(self) -> bool:
        return self._viewer is not None and self._viewer[1] > 0

    @property
    def can_step_forward(self) -> bool:
        return self._viewer is not None and self._viewer[1] + 1 < len(self.turns[self._viewer[0]].citations)

    # ---- source list ----------------------------------------------------
    def _latest_with_citations(self) -> int | None:
        for i in range(len(self.turns) - 1, -1, -1):
            if self.turns[i].citations:
                return i
        return None

    @property
    def hit_counts(self) -> dict[str, int]:
        """How many citations of the newest cited answer point at each source."""
        i = self._latest_with_citations()
        counts: dict[str, int] = {}
        for c in self.turns[i].citations if i is not None else ():
            counts[c.document_name] = counts.get(c.document_name, 0) + 1
        return counts

    def open_source(self, name: str) -> bool:
        """Open the newest cited answer's first citation from this source; False when it cited none."""
        i = self._latest_with_citations()
        if i is None:
            return False
        for c in self.turns[i].citations:
            if c.document_name == name:
                return self.open_citation(i, c.marker)
        return False

    @property
    def scope_hint(self) -> str:
        n = len(self.sources)
        if not n:
            return ""
        return f"Searching all {n} sources" if n > 1 else "Searching 1 source"

    @property
    def busy_text(self) -> str:
        n = len(self.sources)
        return f"Answering from {n} sources…" if n > 1 else "Working…"

    # ---- executor callbacks (GUI thread) --------------------------------
    def _on_ok(self, turn: Turn, result: object) -> None:
        assert isinstance(result, AnswerResult)
        turn.result = result
        turn.state = ViewState.INSUFFICIENT if result.insufficient else ViewState.ANSWER
        self._notify()

    def _on_err(self, turn: Turn, exc: Exception) -> None:
        kind = exc.kind if isinstance(exc, AskQuestionError) else "other"
        turn.error_title = _ERROR_TITLE.get(kind, "Could not get an answer")
        turn.error_message = _ERROR_TEXT.get(kind) or f"Something went wrong: {exc}"
        turn.state = ViewState.ERROR
        self._notify()

    # ---- derived text for the view --------------------------------------
    @staticmethod
    def status_for(turn: Turn | None) -> str:
        if turn is None:
            return ""
        if turn.state is ViewState.BUSY:
            return "Working…"
        if not turn.result:
            return ""
        total = turn.result.latency_ms.get("total")
        parts = []
        if total is not None:
            parts.append(f"Total latency {total / 1000:.1f} s")
        model = turn.result.model_used
        if model and turn.result.fallback_used:
            model += " (fallback)"
        parts.append(f"model: {model or 'none (no model call)'}")
        return " · ".join(parts)

    @property
    def status_line(self) -> str:
        return self.status_for(self._current)

    @staticmethod
    def segments(turn: Turn) -> list[Segment]:
        """The answer split at its markers. Only markers that name one of the turn's citations become chips;
        bracketed numbers inside code blocks or inline code stay text (the citation checks' own rule)."""
        if turn.state is not ViewState.ANSWER or not turn.result:
            return []
        known = {c.marker for c in turn.citations}
        out: list[Segment] = []
        text, pos = turn.result.answer, 0
        for start, end, marker in marker_spans(text):
            if marker not in known:
                continue
            if start > pos:
                out.append(Segment(text[pos:start]))
            out.append(Segment(text[start:end], marker))
            pos = end
        if pos < len(text):
            out.append(Segment(text[pos:]))
        return out

    @property
    def can_copy(self) -> bool:
        return self.state is ViewState.ANSWER

    @property
    def copy_text(self) -> str:
        return self.result.answer if self.can_copy and self.result else ""

    def copy_text_for(self, index: int) -> str:
        """A real answer with its sources listed under it; empty for anything that is not an answer."""
        if not 0 <= index < len(self.turns):
            return ""
        turn = self.turns[index]
        if turn.state is not ViewState.ANSWER or not turn.result:
            return ""
        lines = [turn.result.answer]
        if turn.citations:
            lines += ["", "Sources:"] + [f"[{c.marker}] {c.document_name} — {c.location}" for c in turn.citations]
        return "\n".join(lines)
