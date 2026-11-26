"""answer_v3: plain text with [n] markers and the [[INSUFFICIENT]] sentinel (plan §6.2). Offline doubles only."""
from pathlib import Path

import pytest

from knowledge_assistant.application.generation.answer_question import (
    AnswerQuestion,
    load_messages,
    parse_answer_text,
)
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder, split_format
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import GenerationError
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

ROOT = Path(__file__).resolve().parents[3]
PROMPTS = ROOT / "config" / "prompts"
MESSAGES = load_messages(ROOT / "config" / "messages.json")


def _service(llm, k=5):
    chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i}.", ("Doc", f"Part {i}")) for i in range(1, 8)]
    store = InMemoryVectorStore({c.chunk_id: 0.8 - n / 100 for n, c in enumerate(chunks)})
    store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
    ticks = iter(range(1000))
    return AnswerQuestion(Retriever(FakeEmbedder(), store, top_k=k), llm, PromptBuilder.from_dir(PROMPTS, "answer_v3"),
                          MESSAGES, 0.5, clock=lambda: next(ticks) / 1000)


def test_answer_v3_is_text_format_and_the_format_line_is_not_sent():
    builder = PromptBuilder.from_dir(PROMPTS, "answer_v3")
    assert builder.answer_format == "text"
    assert "answer_format" not in builder.template
    assert PromptBuilder.from_dir(PROMPTS, "answer_v2").answer_format == "json"


def test_fixed_instructions_come_before_anything_that_varies():
    """Prompt-cache friendly (plan §6.4 item 5): the language, passages and question all come after the rules."""
    template = PromptBuilder.from_dir(PROMPTS, "answer_v3").template
    rules_end = template.index("CONTEXT:")
    assert all(template.index(p) > rules_end for p in ("{answer_language}", "{passages}", "{question}"))


def test_unknown_format_is_refused():
    with pytest.raises(ValueError, match="unknown answer_format"):
        split_format("<!-- answer_format: yaml -->\nbody")


def test_valid_markers_become_citations_and_no_schema_is_sent():
    llm = FakeLLM("Part two says so [2]. Part one too [1].")
    result = _service(llm).ask("What does part two say?")
    [request] = llm.requests
    assert request.response_schema is None
    assert not result.insufficient
    assert [c.marker for c in result.citations] == [2, 1]
    assert result.dropped_markers == () and result.uncited_sentences == 0


def test_out_of_range_marker_is_removed_and_the_rest_is_kept():
    result = _service(FakeLLM("Fact [2]. Wrong [9].")).ask("Q?")
    assert result.answer == "Fact [2]. Wrong."
    assert result.dropped_markers == (9,) and [c.marker for c in result.citations] == [2]


def test_non_numeric_marker_is_plain_text_and_not_a_citation():
    result = _service(FakeLLM("Fact [a]. Other [x1].")).ask("Q?")
    assert not result.insufficient and result.citations == () and result.dropped_markers == ()
    assert result.answer == "Fact [a]. Other [x1]."


def test_answer_without_marker_is_shown_with_no_citation():
    result = _service(FakeLLM("A fact with no source.")).ask("Q?")
    assert not result.insufficient and result.answer == "A fact with no source." and result.citations == ()
    assert result.uncited_sentences == 1  # counted as a citation failure by the evaluation


def test_sentinel_on_the_first_line_is_a_refusal_with_its_note():
    result = _service(FakeLLM("[[INSUFFICIENT]]\nThe passages do not give the version number [3].")).ask("Q?")
    assert result.insufficient and result.insufficient_reason == "llm"
    assert result.answer == MESSAGES["en"]
    assert result.missing_information == "The passages do not give the version number [3]."
    assert [c.marker for c in result.citations] == [3]  # related content only (D2)


def test_sentinel_after_leading_blank_lines_and_on_the_same_line_as_the_note():
    data = parse_answer_text("\n\n  [[INSUFFICIENT]] no date given")
    assert data["insufficient"] and data["missing_information"] == "no date given"


def test_sentinel_later_in_the_text_is_ordinary_text():
    data = parse_answer_text("Answer [1].\n[[INSUFFICIENT]]")
    assert not data["insufficient"] and data["answer"] == "Answer [1].\n[[INSUFFICIENT]]"


@pytest.mark.parametrize("text", ["", "   \n ", None])
def test_empty_reply_is_a_generation_error(text):
    with pytest.raises(GenerationError):
        parse_answer_text(text)
