"""scripts/generation/smoke_check.py: the guards that protect the live quota, with fakes (RAG-003 addendum 6).

The smoke check is live and spends at most 5 LLM requests and 0 embedding requests: dev questions only, every query
embedding already cached, one LLM call per step (no retries, no fallback), stop at the first provider error.
"""
import importlib.util
import json
from contextlib import nullcontext
from pathlib import Path

import pytest

from knowledge_assistant.core.exceptions import LLMQuotaError
from knowledge_assistant.core.interfaces.llm import LLMRequest
from knowledge_assistant.core.models import AnswerResult, Citation, RetrievedChunk
from tests.fakes import FakeLLM, make_chunk

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("smoke_check_script", ROOT / "scripts" / "generation" / "smoke_check.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

REPLY = json.dumps({"insufficient": False, "answer": "It says so [1].", "cited_passages": [1], "missing_information": ""})
INSUFFICIENT = json.dumps({"insufficient": True, "answer": "", "cited_passages": [1],
                           "missing_information": "The passages do not cover this."})
CASES = {
    "Q-DEV-001": {"id": "Q-DEV-001", "split": "dev", "language": "en", "question": "What does the guide say?"},
    "Q-DEV-002": {"id": "Q-DEV-002", "split": "dev", "language": "vi", "question": "Hướng dẫn nói gì?"},
    "Q-DEV-005": {"id": "Q-DEV-005", "split": "dev", "language": "en", "question": "An unanswerable question?"},
}


@pytest.fixture(autouse=True)
def logs_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))  # a provider error body is saved here, never in data/logs


class CacheOnlyEmbedder:
    def __init__(self, missing=()):
        self._missing = list(missing)

    def missing(self, texts, task):
        return [t for t in texts if t in self._missing]


class StubService:
    """AnswerQuestion in miniature: the unanswerable question is gate-refused unless the gate is off."""

    def __init__(self, gate_off, llm):
        self.gate_off, self.llm = gate_off, llm
        self.threshold = float("-inf") if gate_off else 0.686

    def ask(self, question):
        refused = "unanswerable" in question and not self.gate_off
        chunk = make_chunk("01", 1, "Passage body 1.", ("Doc", "Part 1"))
        hit = RetrievedChunk(chunk=chunk, rank=1, score=0.3 if "unanswerable" in question else 0.8)
        common = dict(question=question, language="en", retrieved=(hit,), dropped_markers=(), uncited_sentences=0,
                      prompt_version="answer_v2")
        if refused:
            return AnswerResult(answer="Not enough information.", insufficient=True, insufficient_reason="retrieval_gate",
                                missing_information=None, citations=(), latency_ms={"total": 1.0}, llm=None, **common)
        response = self.llm.generate(LLMRequest(prompt=f"PROMPT for {question}"))
        data = json.loads(response.text)
        citation = Citation("01", "Document 01", "Doc > Part 1", "Passage body 1.", chunk.chunk_id, 1, "https://x.invalid")
        return AnswerResult(
            answer="Not enough information." if data["insufficient"] else data["answer"], insufficient=data["insufficient"],
            insufficient_reason="llm" if data["insufficient"] else None,
            missing_information=data["missing_information"] or None, citations=(citation,),
            latency_ms={"generate": 5.0, "retry_wait": 0.0, "throttle_wait": 0.0, "total": 6.0}, llm=response, **common)


def run_smoke(*, embedder=None, answer_llm=None, fallback_llm=None, budget=5, process_check=None):
    lines = []
    services = []

    def build_service(arm, gate_off, llm):
        service = StubService(gate_off, llm)
        services.append((arm, gate_off))
        return service

    code = smoke.run_smoke(
        CASES,
        embedder=embedder or CacheOnlyEmbedder(),
        build_service=build_service,
        answer_llm=answer_llm or FakeLLM(REPLY, model="answer-fake"),
        fallback_llm=fallback_llm or FakeLLM(REPLY, model="fallback-fake"),
        emit=lines.append,
        budget_limit=budget,
        process_check=process_check,
    )
    return code, "\n".join(lines), services


def test_the_real_dev_file_holds_the_three_smoke_cases_and_only_dev_cases():
    cases = smoke.load_dev_cases(smoke.DEV_FILE)
    assert {"Q-DEV-001", "Q-DEV-002", "Q-DEV-005"} <= set(cases)
    assert all(case["split"] == "dev" and case["id"].startswith("Q-DEV-") for case in cases.values())


@pytest.mark.parametrize(
    "case",
    [{"id": "Q-DEV-009", "split": "held-out", "question": "x"}, {"id": "Q-OTHER-001", "split": "dev", "question": "x"}],
    ids=["other-split", "other-id-prefix"],
)
def test_a_case_that_is_not_a_dev_case_is_refused(tmp_path, case):
    """The eval-set firewall: only split=dev and a Q-DEV- id are ever read (fixtures here are made up)."""
    path = tmp_path / "questions.jsonl"
    path.write_text(json.dumps(case) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="refusing"):
        smoke.load_dev_cases(path)


def test_it_stops_before_any_llm_call_when_a_query_embedding_is_not_cached():
    answer, fallback = FakeLLM(REPLY), FakeLLM(REPLY)
    code, text, services = run_smoke(embedder=CacheOnlyEmbedder(missing=[CASES["Q-DEV-002"]["question"]]),
                                     answer_llm=answer, fallback_llm=fallback)
    assert code == 1 and answer.requests == [] and fallback.requests == []
    assert "not cached" in text and services == []


def test_the_full_run_makes_four_llm_requests_and_labels_itself_a_smoke_check():
    answer, fallback = FakeLLM(REPLY, REPLY, INSUFFICIENT, model="answer-fake"), FakeLLM(REPLY, model="fallback-fake")
    code, text, services = run_smoke(answer_llm=answer, fallback_llm=fallback)
    assert code == 0
    assert len(answer.requests) == 3 and len(fallback.requests) == 1  # a1, a2, c on the answer model; d on the fallback
    assert "smoke check, not evaluation data" in text
    assert services == [("A", False)] * 4 + [("A", True)]  # a1, a2, b (text), b (--json), c; only c has the gate off
    assert fallback.requests[0] == answer.requests[0]  # d sends the exact request of a1


def test_the_gate_refusal_step_makes_no_llm_request_and_the_gate_off_step_does():
    answer = FakeLLM(REPLY, REPLY, INSUFFICIENT, model="answer-fake")
    _, text, _ = run_smoke(answer_llm=answer)
    b = text.split("### b.")[1].split("### c.")[0]
    c = text.split("### c.")[1].split("### d.")[0]
    assert "LLM requests this step: 0" in b and "retrieval_gate" in b
    assert "LLM requests this step: 1" in c and "GATE OFF" in c


def test_step_c_reports_the_d2_facts_from_the_model_output():
    answer = FakeLLM(REPLY, REPLY, INSUFFICIENT, model="answer-fake")
    _, text, _ = run_smoke(answer_llm=answer)
    c = text.split("### c.")[1].split("### d.")[0]
    assert "insufficient=true" in c and "missing_information non-empty: yes" in c and "related-only citations printed: 1" in c


def test_step_d_reports_the_fallback_model_thoughts_tokens_and_latency():
    _, text, _ = run_smoke(fallback_llm=FakeLLM(REPLY, model="fallback-fake"))
    d = text.split("### d.")[1]
    assert "fallback-fake" in d and "thoughts tokens" in d and "latency" in d.lower() and "JSON valid: yes" in d


def test_step_d_reports_unusable_fallback_output_instead_of_hiding_it():
    _, text, _ = run_smoke(fallback_llm=FakeLLM("not json at all", model="fallback-fake"))
    d = text.split("### d.")[1]
    assert "JSON valid: no" in d


def test_it_stops_at_the_first_provider_error_and_makes_no_further_request():
    class QuotaLLM:
        def __init__(self):
            self.requests = []

        def generate(self, request):
            self.requests.append(request)
            raise LLMQuotaError("quota used up", daily=True, provider_body='{"status": "RESOURCE_EXHAUSTED"}')

    answer, fallback = QuotaLLM(), FakeLLM(REPLY)
    code, text, _ = run_smoke(answer_llm=answer, fallback_llm=fallback)
    assert code == 2 and len(answer.requests) == 1 and fallback.requests == []
    assert "STOPPED" in text and "quota" in text


def test_the_budget_refuses_a_request_over_the_limit():
    answer = FakeLLM(REPLY, REPLY, INSUFFICIENT, model="answer-fake")
    code, text, _ = run_smoke(answer_llm=answer, budget=2)
    assert code == 3 and len(answer.requests) == 2
    assert "budget" in text.lower() and "STOPPED" in text


def test_the_process_check_runs_only_after_the_gate_refusal_was_confirmed():
    calls = []
    run_smoke(process_check=lambda question: calls.append(question) or (0, "{}"))
    assert calls == [CASES["Q-DEV-005"]["question"]]
    calls.clear()
    # the gate did not refuse b (a stub whose question is not "unanswerable"): no subprocess that could spend quota
    cases = dict(CASES, **{"Q-DEV-005": dict(CASES["Q-DEV-005"], question="An answerable-looking question?")})
    smoke.run_smoke(cases, embedder=CacheOnlyEmbedder(), build_service=lambda a, g, llm: StubService(g, llm),
                    answer_llm=FakeLLM(REPLY, REPLY, REPLY, REPLY), fallback_llm=FakeLLM(REPLY), emit=lambda t: None,
                    budget_limit=5, process_check=lambda q: calls.append(q) or (0, "{}"))
    assert calls == []
