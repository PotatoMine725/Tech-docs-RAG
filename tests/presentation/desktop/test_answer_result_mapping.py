"""RAG-002 addendum 2: a real core AnswerResult maps onto the GUI-001-pre contract without losing a field the GUI
shows. The mapping below is a test-only sketch; the real adapter belongs to GUI-001 wiring (report lists mismatches)."""
import dataclasses
import json
from pathlib import Path

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.models import AnswerResult
from knowledge_assistant.presentation.desktop.viewmodels import contracts
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

ROOT = Path(__file__).resolve().parents[3]


def to_gui(result: AnswerResult) -> contracts.AnswerResult:
    return contracts.AnswerResult(
        question=result.question,
        language=result.language,
        answer=result.answer,
        insufficient=result.insufficient,
        insufficient_reason=result.insufficient_reason,
        missing_information=result.missing_information,
        citations=tuple(
            contracts.Citation(c.marker, c.document_name, c.location, c.excerpt, c.source_url,
                               related_only=result.insufficient)
            for c in result.citations
        ),
        latency_ms=dict(result.latency_ms),
        model_used=result.llm.model_used if result.llm else None,
    )


def _ask(reply: dict) -> AnswerResult:
    chunks = [make_chunk(f"{i:02d}", i, f"Body {i}.") for i in range(1, 6)]
    store = InMemoryVectorStore({c.chunk_id: 0.9 - i / 100 for i, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * 5)
    service = AnswerQuestion(
        Retriever(FakeEmbedder(), store), FakeLLM(json.dumps(reply)),
        PromptBuilder.from_dir(ROOT / "config" / "prompts", "answer_v1"),
        load_messages(ROOT / "config" / "messages.json"), threshold=0.0,
    )
    return service.ask("Question?")


def test_every_gui_field_is_filled_from_the_core_result():
    core = _ask({"insufficient": False, "answer": "A [1]. B [2].", "cited_passages": [1, 2],
                 "missing_information": "C is not covered."})
    gui = to_gui(core)
    gui_fields = {f.name for f in dataclasses.fields(contracts.AnswerResult)}
    core_fields = {f.name for f in dataclasses.fields(AnswerResult)}
    assert gui_fields - core_fields == {"model_used"}  # flattened from AnswerResult.llm
    assert [(c.marker, c.location, c.source_url, c.related_only) for c in gui.citations] == [
        (1, "Doc > Section", "https://example.invalid/01", False),
        (2, "Doc > Section", "https://example.invalid/02", False),
    ]
    assert gui.model_used == "fake-llm" and gui.missing_information == "C is not covered."


def test_insufficient_citations_become_related_only():
    core = _ask({"insufficient": True, "answer": "", "cited_passages": [4], "missing_information": "Not covered."})
    gui = to_gui(core)
    assert gui.insufficient and [c.related_only for c in gui.citations] == [True]
