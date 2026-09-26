"""RAG-003: core LLMError kinds map 1:1 onto the GUI's AskQuestionError kinds (RAG-002 report, mismatch 4).

The wiring that catches an LLMError and raises AskQuestionError(error.kind, ...) is GUI-001's job; these tests fix
the contract it relies on: the kind strings are identical, and the view-model shows the right message for each.
"""
import pytest

from knowledge_assistant.core.exceptions import (
    GenerationError,
    LLMError,
    LLMQuotaError,
    LLMRequestError,
    LLMUnavailableError,
    RetrievalError,
)
from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, ViewState
from knowledge_assistant.presentation.desktop.viewmodels.contracts import AskQuestionError

MAPPING = [
    (LLMQuotaError("quota"), "quota"),
    (LLMUnavailableError("down"), "unavailable"),
    (LLMRequestError("bad request"), "other"),
    (LLMError("unclassified"), "other"),
]


def sync_executor(fn, on_ok, on_err):
    try:
        result = fn()
    except Exception as exc:  # noqa: BLE001
        on_err(exc)
    else:
        on_ok(result)


class RaisingPort:
    """The GUI-001 wiring in miniature: an LLMError from the use case becomes AskQuestionError(kind)."""

    def __init__(self, error: LLMError) -> None:
        self._error = error

    def ask(self, question: str, arm: str):
        try:
            raise self._error
        except LLMError as error:
            raise AskQuestionError(error.kind, str(error)) from error


@pytest.mark.parametrize(("error", "kind"), MAPPING, ids=lambda v: v if isinstance(v, str) else type(v).__name__)
def test_each_llm_error_kind_is_the_gui_kind_of_the_same_name(error, kind):
    assert error.kind == kind
    assert AskQuestionError(error.kind, str(error)).kind == kind


def test_the_three_llm_error_kinds_are_exactly_the_provider_kinds_of_the_gui_contract():
    assert {LLMQuotaError.kind, LLMUnavailableError.kind, LLMRequestError.kind} == {"quota", "unavailable", "other"}


def test_the_view_model_shows_quota_and_unavailable_texts_and_a_generic_text_for_other():
    titles = {}
    for error, kind in MAPPING:
        vm = AskViewModel(RaisingPort(error), sync_executor)
        vm.submit("question")
        assert vm.state is ViewState.ERROR
        titles[kind] = vm.error_title
    assert titles["quota"] == "Quota used up"
    assert titles["unavailable"] == "Model service unavailable"
    assert titles["other"] == "Could not get an answer"


def test_errors_outside_the_llm_stay_other_for_the_gui():
    """GenerationError (unusable output) is not an LLMError; the wiring maps it to `other` (RAG-002 report)."""
    assert not issubclass(GenerationError, LLMError) and not issubclass(RetrievalError, LLMError)
