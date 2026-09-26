from pathlib import Path

import pytest

from knowledge_assistant.application.generation.prompt_builder import (
    PromptBuilder,
    build_prompt,
    load_template,
    render_passages,
)
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import make_chunk

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "config" / "prompts"
TEMPLATE = "Lang={answer_language}\nCONTEXT:\n{passages}\n\nQUESTION: {question}\n"


def _hits():
    return (
        RetrievedChunk(make_chunk("03", 1, "First {body}.", ("Guide", "Setup"), document_name="Guide"), 1, 0.9),
        RetrievedChunk(make_chunk("08", 2, "Second body.", ("Ref", "API", "Options"), document_name="Ref"), 2, 0.8),
    )


def test_snapshot_passages_in_rank_order_with_heading_paths():
    assert render_passages(_hits()) == "[1] Guide — Guide > Setup\nFirst {body}.\n\n[2] Ref — Ref > API > Options\nSecond body."


def test_snapshot_full_prompt():
    prompt = build_prompt(TEMPLATE, "How {question} works?", "vi", _hits())
    assert prompt == (
        "Lang=Vietnamese\nCONTEXT:\n"
        "[1] Guide — Guide > Setup\nFirst {body}.\n\n[2] Ref — Ref > API > Options\nSecond body."
        "\n\nQUESTION: How {question} works?\n"
    )


def test_prompt_contains_only_the_retrieved_passages():
    hits = _hits()
    prompt = build_prompt(TEMPLATE, "q", "en", hits[:1])
    assert "First {body}." in prompt and "Second body." not in prompt and "[2]" not in prompt


def test_versioned_template_file_loads_and_renders_without_leftover_placeholders():
    builder = PromptBuilder.from_dir(PROMPTS_DIR, "answer_v1")
    assert builder.version == "answer_v1"
    prompt = builder.build("What is X?", "en", _hits())
    for placeholder in ("{answer_language}", "{passages}", "{question}"):
        assert placeholder not in prompt
    assert "Write \"answer\" and \"missing_information\" in English." in prompt
    assert prompt.rstrip().endswith("QUESTION: What is X?")


def test_template_without_placeholders_is_rejected(tmp_path):
    (tmp_path / "bad.md").write_text("no placeholders", encoding="utf-8")
    with pytest.raises(ValueError):
        load_template(tmp_path, "bad")
