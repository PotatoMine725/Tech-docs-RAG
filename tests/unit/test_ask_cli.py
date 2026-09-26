"""scripts/ask.py with a fake service: output shape, --json, --gate-off, exit codes, the key never printed (RAG-003)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.generation.answer_question import AnswerQuestion, load_messages
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder
from knowledge_assistant.application.retrieval.retrieve import Retriever
from knowledge_assistant.core.exceptions import (
    ConfigurationError,
    GenerationError,
    LLMQuotaError,
    LLMUnavailableError,
    VectorStoreError,
)
from tests.fakes import FakeEmbedder, FakeLLM, InMemoryVectorStore, make_chunk

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ask_script", ROOT / "scripts" / "ask.py")
ask = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ask)

KEY = "AIza" + "k" * 35
MESSAGES = load_messages(ROOT / "config" / "messages.json")
REPLY = json.dumps({"insufficient": False, "answer": "Part one says so [1].", "cited_passages": [1],
                    "missing_information": ""})
INSUFFICIENT = json.dumps({"insufficient": True, "answer": "", "cited_passages": [2],
                           "missing_information": "The passages do not cover this."})


class Factory:
    """Stands in for the real wiring: records (arm, gate_off), serves a fake service and its LLM."""

    def __init__(self, llm, top_score=0.8, threshold=0.5):
        self.llm, self.top_score, self.threshold = llm, top_score, threshold
        self.calls = []

    def __call__(self, arm, gate_off):
        self.calls.append((arm, gate_off))
        chunks = [make_chunk(f"{i:02d}", i, f"Passage body {i}. " * 30, ("Doc", f"Part {i}")) for i in range(1, 7)]
        store = InMemoryVectorStore({c.chunk_id: self.top_score - n / 100 for n, c in enumerate(chunks)})
        store.upsert(chunks, [[1.0, 0.0]] * len(chunks))
        service = AnswerQuestion(
            Retriever(FakeEmbedder(), store, top_k=5), self.llm,
            PromptBuilder.from_dir(ROOT / "config" / "prompts", "answer_v2"), MESSAGES,
            float("-inf") if gate_off else self.threshold,
        )
        return contextlib.nullcontext((service, self.llm))


def run(argv, factory):
    out, err = io.StringIO(), io.StringIO()
    code = ask.main(argv, factory=factory, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture(autouse=True)
def logs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))


def test_text_output_has_answer_numbered_citations_flag_latency_model_and_tokens():
    code, out, _ = run(["What does part one say?"], Factory(FakeLLM(REPLY)))
    assert code == 0
    assert "Answer:\nPart one says so [1]." in out
    assert "[1] Document 01 — Doc > Part 1" in out  # document, heading path
    assert "Passage body 1." in out  # excerpt
    assert "Insufficient information: no" in out
    latency = [line for line in out.splitlines() if line.startswith("Latency (ms):")][0]
    for stage in ("embed_query", "retrieve", "generate", "retry_wait", "throttle_wait", "total"):
        assert stage in latency
    assert "Model: fake-llm (retries 0, fallback no)" in out
    assert "Tokens: prompt" in out and "thoughts n/a" in out  # thoughts tokens not reported by the fake


def test_the_excerpt_is_the_original_english_passage_prefix_in_text_and_json():
    _, text, _ = run(["Q?"], Factory(FakeLLM(REPLY)))
    _, raw, _ = run(["Q?", "--json"], Factory(FakeLLM(REPLY)))
    excerpt = json.loads(raw)["citations"][0]["excerpt"]
    assert excerpt.startswith("Passage body 1.") and len(excerpt) <= 300  # bounded by the citation builder
    assert " ".join(excerpt.split()) in text


def test_json_output_is_one_json_document_with_the_accounting_fields():
    code, out, _ = run(["What does part one say?", "--json"], Factory(FakeLLM(REPLY)))
    data = json.loads(out)
    assert code == 0
    assert data["answer"] == "Part one says so [1]." and data["insufficient"] is False
    assert data["arm"] == "A" and data["language"] == "en" and data["llm_called"] is True
    assert data["model_used"] == "fake-llm" and data["retry_count"] == 0 and data["fallback_used"] is False
    assert set(data["tokens"]) == {"prompt", "output", "thoughts"} and data["tokens"]["thoughts"] is None
    assert {"embed_query", "retrieve", "generate", "retry_wait", "throttle_wait", "total"} <= set(data["latency_ms"])
    [citation] = data["citations"]
    assert (citation["marker"], citation["document_name"], citation["location"]) == (1, "Document 01", "Doc > Part 1")
    assert citation["related_only"] is False
    assert data["retrieval"]["gate_off"] is False and data["retrieval"]["threshold"] == 0.5


def test_a_vietnamese_question_prints_unescaped_vietnamese():
    code, out, _ = run(["Dependency injection là gì?", "--json"], Factory(FakeLLM(REPLY), top_score=0.3))
    data = json.loads(out)
    assert data["language"] == "vi" and data["insufficient_reason"] == "retrieval_gate"
    assert data["answer"] == MESSAGES["vi"] and "Bộ tài liệu" in out  # not \u-escaped


def test_the_retrieval_gate_refusal_says_no_llm_was_called():
    llm = FakeLLM(REPLY)
    code, out, _ = run(["Something unrelated?"], Factory(llm, top_score=0.3))
    assert code == 0 and llm.requests == []
    assert "Insufficient information: yes (retrieval_gate)" in out
    assert "Model: none (no LLM call: the retrieval gate refused)" in out


def test_arm_is_passed_on_and_defaults_to_a():
    factory = Factory(FakeLLM(REPLY))
    run(["Q?"], factory)
    run(["Q?", "--arm", "B"], factory)
    assert factory.calls == [("A", False), ("B", False)]
    with pytest.raises(SystemExit) as exit_info:
        run(["Q?", "--arm", "C"], factory)
    assert exit_info.value.code == 2


def test_gate_off_is_a_labelled_diagnostic_that_sends_a_low_score_question_to_the_llm():
    llm = FakeLLM(INSUFFICIENT)
    factory = Factory(llm, top_score=0.3)
    code, out, _ = run(["Something unrelated?", "--gate-off"], factory)
    assert code == 0 and factory.calls == [("A", True)] and len(llm.requests) == 1
    assert "GATE OFF" in out and "diagnostic" in out
    assert "Insufficient information: yes (llm)" in out
    assert "The passages do not cover this." in out  # missing_information kept (D2)
    assert "related content only" in out and "[2] Document 02 — Doc > Part 2" in out
    _, raw, _ = run(["Something unrelated?", "--gate-off", "--json"], Factory(FakeLLM(INSUFFICIENT), top_score=0.3))
    data = json.loads(raw)
    assert data["retrieval"]["gate_off"] is True and data["retrieval"]["threshold"] is None
    assert data["citations"][0]["related_only"] is True


def test_without_gate_off_the_same_question_is_refused_by_the_gate():
    llm = FakeLLM(INSUFFICIENT)
    _, out, _ = run(["Something unrelated?"], Factory(llm, top_score=0.3))
    assert "GATE OFF" not in out and llm.requests == []


@pytest.mark.parametrize(
    ("error", "code", "kind"),
    [
        (LLMQuotaError("quota used up", daily=True, provider_body='{"status": "RESOURCE_EXHAUSTED"}'), 2, "quota"),
        (LLMUnavailableError("model unavailable"), 2, "unavailable"),
        (GenerationError("not JSON", raw_text="oops"), 3, "generation"),
        (VectorStoreError("collection missing"), 4, "setup"),
        (ConfigurationError("GEMINI_API_KEY is not set"), 4, "setup"),
    ],
    ids=["quota", "unavailable", "generation", "vector-store", "configuration"],
)
def test_failures_exit_nonzero_with_a_readable_message_and_no_traceback(error, code, kind):
    class Failing:
        def generate(self, request):
            raise error

    factory = Factory(Failing())
    if isinstance(error, (VectorStoreError, ConfigurationError)):
        def factory(arm, gate_off):  # noqa: F811
            raise error
    got, out, err = run(["Q?"], factory)
    assert got == code and out == ""
    assert "Traceback" not in err and str(error) in err and kind in err


def test_a_json_run_reports_a_failure_as_a_json_error_object():
    class Failing:
        def generate(self, request):
            raise LLMUnavailableError("model unavailable")

    code, out, _ = run(["Q?", "--json"], Factory(Failing()))
    assert code == 2 and json.loads(out) == {"error": {"kind": "unavailable", "message": "model unavailable"}}


def test_a_provider_error_body_is_saved_redacted_and_the_key_is_never_printed(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", KEY)

    class Failing:
        def generate(self, request):
            raise LLMQuotaError(f"quota {KEY}", daily=True, provider_body=f'{{"message": "key {KEY}"}}')

    code, out, err = run(["Q?"], Factory(Failing()))
    assert code == 2 and KEY not in out + err
    [saved] = list((tmp_path / "logs").glob("ask-quota-*.txt"))
    assert KEY not in saved.read_text(encoding="utf-8") and "[REDACTED]" in saved.read_text(encoding="utf-8")
    assert saved.name in err  # the message names the file


@pytest.mark.parametrize("argv", [["Q?"], ["Q?", "--json"], ["Q?", "--gate-off"]])
def test_the_key_is_never_printed_on_success(monkeypatch, argv):
    monkeypatch.setenv("GEMINI_API_KEY", KEY)
    _, out, err = run(argv, Factory(FakeLLM(REPLY)))
    assert KEY not in out + err


def test_no_question_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_info:
        run([], Factory(FakeLLM(REPLY)))
    assert exit_info.value.code == 2
