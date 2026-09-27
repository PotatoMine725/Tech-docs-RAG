"""GUI-001: the ONE adapter core AnswerResult -> contracts.AnswerResult, one test per RAG-002 mismatch (1-7)."""
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import (
    ConfigurationError,
    EmbeddingError,
    GenerationError,
    LLMError,
    LLMQuotaError,
    LLMRequestError,
    LLMUnavailableError,
    RetrievalError,
    VectorStoreError,
)
from knowledge_assistant.core.interfaces.llm import LLMResponse
from knowledge_assistant.presentation.desktop.viewmodels import contracts
from knowledge_assistant.presentation.desktop.viewmodels.ask_viewmodel import AskViewModel, ViewState
from knowledge_assistant.presentation.desktop.viewmodels.core_ask_question import CoreAskQuestion, to_gui_result
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

ROOT = Path(__file__).resolve().parents[3]


def _service(reply: dict | None, threshold: float = 0.0, llm=None) -> AnswerQuestion:
    chunks = [make_chunk(f"{i:02d}", i, f"Body {i}.") for i in range(1, 6)]
    store = InMemoryVectorStore({c.chunk_id: 0.9 - i / 100 for i, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * 5)
    return AnswerQuestion(
        Retriever(FakeEmbedder(), store), llm or FakeLLM(json.dumps(reply)),
        PromptBuilder.from_dir(ROOT / "config" / "prompts", "answer_v2"),
        load_messages(ROOT / "config" / "messages.json"), threshold=threshold,
    )


ANSWER = {"insufficient": False, "answer": "A [1]. B [2].", "cited_passages": [1, 2], "missing_information": ""}
INSUFFICIENT = {"insufficient": True, "answer": "", "cited_passages": [1], "missing_information": "Nothing on C."}


def test_1_citations_of_an_answer_are_not_related_only():
    gui = to_gui_result(_service(ANSWER).ask("Question?"))
    assert [c.related_only for c in gui.citations] == [False, False]


def test_1_related_only_equals_insufficient_for_every_citation():
    gui = to_gui_result(_service(INSUFFICIENT).ask("Question?"))
    assert gui.insufficient and gui.insufficient_reason == "llm"
    assert gui.citations and all(c.related_only for c in gui.citations)
    assert gui.missing_information == "Nothing on C."


def test_2_model_used_comes_from_the_llm_response():
    gui = to_gui_result(_service(ANSWER).ask("Question?"))
    assert gui.model_used == "fake-llm" and gui.fallback_used is False


def test_2_model_used_is_none_when_the_gate_answered():
    gui = to_gui_result(_service(ANSWER, threshold=2.0).ask("Question?"))  # top-1 score < threshold: no LLM call
    assert gui.insufficient and gui.insufficient_reason == "retrieval_gate"
    assert gui.model_used is None and gui.fallback_used is False and gui.citations == ()


def test_2_fallback_flag_is_carried():
    class FallbackLLM(FakeLLM):
        def generate(self, request):
            r = super().generate(request)
            return LLMResponse(r.text, "gemini-3.5-flash", 3, True, None, None, 1.0)

    gui = to_gui_result(_service(ANSWER, llm=FallbackLLM(json.dumps(ANSWER))).ask("Question?"))
    assert gui.model_used == "gemini-3.5-flash" and gui.fallback_used is True


def test_3_port_picks_the_service_of_the_arm_and_builds_it_lazily():
    built = []

    def factory(arm):
        built.append(arm)
        return _service(ANSWER)

    port = CoreAskQuestion(factory)
    assert built == []
    port.ask("Question?", "B")
    port.ask("Question again?", "B")
    port.ask("Question?", "A")
    assert built == ["B", "A"]  # one service per arm, each built once, on first use


def test_5_latency_has_no_generate_key_when_the_gate_answered():
    gate = to_gui_result(_service(ANSWER, threshold=2.0).ask("Question?"))
    assert "generate" not in gate.latency_ms and "total" in gate.latency_ms
    llm = to_gui_result(_service(ANSWER).ask("Question?"))
    assert "generate" in llm.latency_ms


def test_6_7_source_url_and_core_only_fields_are_dropped_without_error():
    gui = to_gui_result(_service(ANSWER).ask("Question?"))
    assert all(isinstance(c.source_url, str) for c in gui.citations)
    assert not hasattr(gui, "retrieved") and not hasattr(gui.citations[0], "chunk_id")


def test_the_language_and_question_are_carried_for_vietnamese():
    gui = to_gui_result(_service(ANSWER, threshold=2.0).ask("Dependency injection là gì?"))
    assert gui.language == "vi" and "không chứa đủ thông tin" in gui.answer


ERRORS = [
    (LLMQuotaError("q"), "quota"),
    (LLMUnavailableError("u"), "unavailable"),
    (LLMRequestError("r"), "other"),
    (LLMError("x"), "other"),
    (RetrievalError("empty"), "no_index"),
    (VectorStoreError("collection missing"), "no_index"),
    (GenerationError("bad json"), "other"),
    (ConfigurationError("no key"), "other"),
    (EmbeddingError("embed"), "other"),
    (RuntimeError("boom"), "other"),
]


@pytest.mark.parametrize(("error", "kind"), ERRORS, ids=lambda v: v if isinstance(v, str) else type(v).__name__)
def test_4_errors_map_to_ask_question_error_kind(error, kind):
    def factory(arm):
        raise error

    with pytest.raises(contracts.AskQuestionError) as caught:
        CoreAskQuestion(factory).ask("Question?", "A")
    assert caught.value.kind == kind
    assert caught.value.__cause__ is error


def test_4_an_error_raised_while_asking_maps_too():
    class Failing:
        threshold = 0.0

        def ask(self, question):
            raise LLMQuotaError("429")

    with pytest.raises(contracts.AskQuestionError) as caught:
        CoreAskQuestion(lambda arm: Failing()).ask("Question?", "A")
    assert caught.value.kind == "quota"


def test_4_view_model_shows_the_mapped_error_states():
    def sync(fn, on_ok, on_err):
        try:
            on_ok(fn())
        except Exception as exc:  # noqa: BLE001
            on_err(exc)

    def factory(arm):
        raise RetrievalError("empty")

    vm = AskViewModel(CoreAskQuestion(factory), sync)
    vm.submit("Question?")
    assert vm.state is ViewState.ERROR and vm.error_title == "Search index not found"


def test_status_line_marks_the_fallback_model():
    def sync(fn, on_ok, on_err):
        on_ok(fn())

    class Port:
        def __init__(self, result):
            self.result = result

        def ask(self, question, arm):
            return self.result

    base = dict(question="q", language="en", answer="a", insufficient=False, latency_ms={"total": 2500.0})
    vm = AskViewModel(Port(contracts.AnswerResult(**base, model_used="gemini-3.5-flash", fallback_used=True)), sync)
    vm.submit("q")
    assert vm.status_line == "Total latency 2.5 s · model: gemini-3.5-flash (fallback)"
    vm = AskViewModel(Port(contracts.AnswerResult(**base, model_used="gemini-3.5-flash-lite")), sync)
    vm.submit("q")
    assert vm.status_line == "Total latency 2.5 s · model: gemini-3.5-flash-lite"
    vm = AskViewModel(Port(contracts.AnswerResult(**base)), sync)
    vm.submit("q")
    assert "none (no model call)" in vm.status_line
