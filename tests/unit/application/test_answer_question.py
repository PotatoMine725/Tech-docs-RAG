"""AnswerQuestion end to end with offline doubles (FakeEmbedder, InMemoryVectorStore, FakeLLM)."""
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import ANSWER_SCHEMA, PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import GenerationError
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

ROOT = Path(__file__).resolve().parents[3]
MESSAGES = load_messages(ROOT / "config" / "messages.json")
EN_MSG = "The document collection does not contain enough information to answer this question."
VI_MSG = "Bộ tài liệu hiện có không chứa đủ thông tin để trả lời câu hỏi này."


def _reply(insufficient=False, answer="", cited=(), missing=""):
    return json.dumps({"insufficient": insufficient, "answer": answer, "cited_passages": list(cited),
                       "missing_information": missing})


def _service(llm, top_score=0.8, threshold=0.5, k=5):
    chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i}.", ("Doc", f"Part {i}")) for i in range(1, 8)]
    scores = {c.chunk_id: top_score - n / 100 for n, c in enumerate(chunks)}
    store = InMemoryVectorStore(scores)
    store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
    ticks = iter(range(1000))
    return AnswerQuestion(
        Retriever(FakeEmbedder(), store, top_k=k), llm, PromptBuilder.from_dir(ROOT / "config" / "prompts", "answer_v1"),
        MESSAGES, threshold, clock=lambda: next(ticks) / 1000,
    )


def test_answer_with_marker_builds_citation_for_that_rank():
    llm = FakeLLM(_reply(answer="Part two says so [2]. This is an out of range claim [7].", cited=[2]))
    result = _service(llm).ask("What does part two say?")
    assert not result.insufficient and result.insufficient_reason is None
    assert result.answer == "Part two says so [2]. This is an out of range claim."
    assert result.dropped_markers == (7,)
    [citation] = result.citations
    assert (citation.marker, citation.location, citation.excerpt) == (2, "Doc > Part 2", "Passage body 2.")
    assert result.uncited_sentences == 1  # the second sentence lost its only marker
    assert result.llm.model_used == "fake-llm"
    assert result.prompt_version == "answer_v1"
    assert set(result.latency_ms) == {"embed_query", "retrieve", "generate", "total"}


def test_prompt_sent_to_llm_has_the_retrieved_passages_in_rank_order_and_the_schema():
    llm = FakeLLM(_reply(answer="Yes [1]."))
    result = _service(llm).ask("Question?")
    [request] = llm.requests
    assert request.response_schema == ANSWER_SCHEMA
    positions = [request.prompt.index(f"[{n}] Document {hit.chunk.source_id} — Doc > Part")
                 for n, hit in enumerate(result.retrieved, start=1)]
    assert positions == sorted(positions) and len(positions) == 5
    assert "Passage body 6." not in request.prompt  # rank 6+ is not a passage


def test_gate_fires_below_threshold_and_llm_is_not_called():
    llm = FakeLLM(_reply(answer="unused [1]."))
    result = _service(llm, top_score=0.40, threshold=0.5).ask("What is this?")
    assert llm.requests == []
    assert result.insufficient and result.insufficient_reason == "retrieval_gate"
    assert result.answer == EN_MSG and result.llm is None and result.citations == ()
    assert "generate" not in result.latency_ms and "total" in result.latency_ms
    assert len(result.retrieved) == 5  # kept for evaluation


def test_gate_does_not_fire_at_or_above_threshold():
    llm = FakeLLM(_reply(answer="Fine [1]."))
    result = _service(llm, top_score=0.5, threshold=0.5).ask("What is this?")
    assert len(llm.requests) == 1 and not result.insufficient


@pytest.mark.parametrize(("question", "message", "language"), [
    ("What is the default port?", EN_MSG, "en"),
    ("Cổng mặc định là gì?", VI_MSG, "vi"),
])
def test_insufficient_message_follows_question_language(question, message, language):
    for llm, threshold in ((FakeLLM(_reply(insufficient=True, missing="x")), 0.0), (FakeLLM(), 0.99)):
        result = _service(llm, threshold=threshold).ask(question)
        assert result.language == language and result.answer == message


def test_llm_insufficient_keeps_missing_information_and_related_citations():
    llm = FakeLLM(_reply(insufficient=True, answer="", cited=[3], missing="The port number is not covered."))
    result = _service(llm).ask("What is the default port?")
    assert result.insufficient and result.insufficient_reason == "llm"
    assert result.answer == EN_MSG
    assert result.missing_information == "The port number is not covered."
    assert [c.marker for c in result.citations] == [3]  # related only (D2), never shown as the answer
    assert result.uncited_sentences == 0


def test_partial_answer_keeps_missing_information():
    llm = FakeLLM(_reply(answer="Half is covered [1].", cited=[1], missing="The other half."))
    result = _service(llm).ask("Two things?")
    assert not result.insufficient and result.missing_information == "The other half."


@pytest.mark.parametrize("raw", [
    "not json at all",
    '{"insufficient": false, "answer": "x"}',  # keys missing
    '{"insufficient": "no", "answer": "x", "cited_passages": [], "missing_information": ""}',
    '{"insufficient": false, "answer": "  ", "cited_passages": [], "missing_information": ""}',
    '["a list"]',
])
def test_unusable_llm_output_raises_generation_error_with_raw_text(raw):
    with pytest.raises(GenerationError) as caught:
        _service(FakeLLM(raw)).ask("Question?")
    assert caught.value.raw_text == raw
