"""RunEvaluation with offline doubles (EVAL-003a): a resumable, model-pure, quota-aware evaluation run.

Every case here is made up (`Q-TEST-nnn`); the frozen question files are never read.
"""
import json
from datetime import datetime, timezone

import pytest

from knowledge_assistant.application.evaluation.records import (
    GROUND_TRUTH_FIELDS,
    LATENCY_STAGES,
    RECORD_FIELDS,
    latest_records,
)
from knowledge_assistant.application.evaluation.run_evaluation import RunConfig, RunEnvironment, RunEvaluation
from knowledge_assistant.core.exceptions import (
    EmbeddingError,
    EvaluationError,
    GenerationError,
    LLMQuotaError,
    LLMRequestError,
    LLMUnavailableError,
    ModelPurityError,
    QuotaExhaustedError,
    RetrievalError,
    RunConfigMismatch,
)
from tests.eval_fakes import (
    ANSWER_MODEL,
    ENVIRONMENT,
    MemoryRecordStore,
    ScriptedLLM,
    ScriptedRetriever,
    answer_json,
    make_answerer,
    make_case,
    make_cases,
    make_config,
    response,
)

FIXED_NOW = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)


class Run:
    """One RunEvaluation on a shared store; `restart()` builds a new one on the same run, like a new process."""

    def __init__(self, llm=None, retriever=None, store=None, mode="full", max_llm_calls=200, threshold=0.5, config=None,
                 progress=None, stats=None, environment=ENVIRONMENT):
        self.store = store or MemoryRecordStore()
        self.retriever = retriever or ScriptedRetriever()
        self.llm = llm or ScriptedLLM()
        self.mode, self.max_llm_calls, self.threshold = mode, max_llm_calls, threshold
        self.config, self.progress, self.stats, self.environment = config, progress, stats, environment
        self.lines: list[str] = []
        self.evaluation = self._build()

    def _build(self):
        answerer = make_answerer(self.retriever, self.llm, self.threshold)
        ticks = iter(range(0, 10_000_000, 2)).__next__  # every clock() call is 2 s after the previous one
        return RunEvaluation(
            "run-1", self.config or make_config(mode=self.mode, threshold=self.threshold), self.store, self.retriever,
            answerer, max_llm_calls=self.max_llm_calls, clock=lambda: float(ticks()), now=lambda: FIXED_NOW,
            progress=self.progress or self.lines.append, stats=self.stats,
        )

    def restart(self, llm=None, **changes):
        self.llm = llm or ScriptedLLM()
        for name, value in changes.items():
            setattr(self, name, value)
        self.evaluation = self._build()
        return self

    def run(self, cases):
        return self.evaluation.run(cases, self.environment)


def final(store) -> dict:
    return latest_records(store.records)


# --- the record -----------------------------------------------------------------------------------------------

def test_a_full_run_writes_one_ok_record_per_case_with_every_schema_field():
    run = Run()
    summary = run.run(make_cases(5))
    assert (summary.ok, summary.errors, summary.stopped, summary.remaining) == (5, 0, None, 0)
    assert len(run.store.records) == 5 and len(run.llm.requests) == 5
    for record in run.store.records:
        assert tuple(record) == RECORD_FIELDS
        assert (record["status"], record["arm"], record["mode"], record["run_id"]) == ("ok", "A", "full", "run-1")
        assert record["split"] == "dev"  # make_config's split
        assert record["error"] is None and record["error_kind"] is None and record["error_model"] is None
    assert [r["case_id"] for r in run.store.records] == [f"Q-TEST-00{n}" for n in range(1, 6)]


def test_every_record_carries_the_split_of_the_run_config_error_records_too():
    for split in ("eval", "dev"):
        llm = ScriptedLLM(LLMRequestError("bad request"))  # case 1 errors, case 2 answers
        run = Run(llm=llm, config=make_config(split=split))
        run.run(make_cases(2))
        assert [r["status"] for r in run.store.records] == ["error", "ok"]
        assert [r["split"] for r in run.store.records] == [split, split]


def test_ground_truth_in_the_records_equals_the_dataset_cases():
    cases = make_cases(3)
    run = Run()
    run.run(cases)
    for case, record in zip(cases, run.store.records):
        assert {field: record[field] for field in GROUND_TRUTH_FIELDS} == {field: case[field] for field in GROUND_TRUTH_FIELDS}
        assert "blueprint_id" not in record and "concepts" not in record  # only the schema's fields are copied


def test_an_answered_record_carries_the_generated_fields_and_the_addendum_fields():
    retriever = ScriptedRetriever(duplicates_dropped=2, duplicate_ids=("01:header-1600:0009",))
    llm = ScriptedLLM(response(answer_json("Part one says so [1].", cited=[1]), retry_count=1, retry_wait_ms=1500.0,
                               throttle_wait_ms=250.0, thoughts_tokens=12))
    run = Run(llm=llm, retriever=retriever)
    run.run([make_case(1)])
    [record] = run.store.records
    assert record["answer"] == "Part one says so [1]." and record["insufficient"] is False
    assert record["insufficient_reason"] is None and record["missing_information"] is None
    assert record["citations"] == [
        {"marker": 1, "chunk_id": "01:header-1600:0001", "source_id": "01", "heading_path": "Doc > Part 1"}]
    assert (record["dropped_markers"], record["uncited_sentences"]) == ([], 0)
    assert (record["llm_called"], record["top1_score"], record["gate_fired"]) == (True, 0.8, False)
    assert record["duplicates_dropped"] == 2
    assert [chunk["rank"] for chunk in record["retrieved"]] == [1, 2, 3, 4, 5]
    first = record["retrieved"][0]
    assert first["display_text"] == "Passage body 1." and first["duplicate_chunk_ids"] == ["01:header-1600:0009"]
    assert len(first["passage_hash"]) == 64 and first["score"] == 0.8 and record["retrieved"][1]["duplicate_chunk_ids"] == []
    assert (record["model_used"], record["retry_count"], record["fallback_used"]) == (ANSWER_MODEL, 1, False)
    assert (record["prompt_tokens"], record["output_tokens"], record["thoughts_tokens"]) == (100, 20, 12)
    assert set(record["latency_ms"]) == set(LATENCY_STAGES)
    assert record["latency_ms"]["retry_wait"] == 1500.0 and record["latency_ms"]["throttle_wait"] == 250.0
    assert record["latency_ms"]["embed_query"] == 2.0 and record["latency_ms"]["total"] is not None
    assert record["prompt_version"] == "answer_v2"
    assert record["started_at"] == record["finished_at"] == FIXED_NOW.isoformat(timespec="milliseconds")


def test_a_case_the_gate_answers_has_no_llm_call_and_still_counts_as_clean_for_latency():
    question = make_case(1)["question"]
    run = Run(retriever=ScriptedRetriever(top_scores={question: 0.4}))
    run.run([make_case(1)])
    [record] = run.store.records
    assert run.llm.requests == []
    assert (record["gate_fired"], record["top1_score"], record["llm_called"]) == (True, 0.4, False)
    assert (record["insufficient"], record["insufficient_reason"]) == (True, "retrieval_gate")
    assert record["citations"] == [] and record["missing_information"] is None and record["model_used"] is None
    assert (record["retry_count"], record["fallback_used"]) == (0, False)
    assert record["latency_ms"]["generate"] is None and record["latency_ms"]["retry_wait"] is None
    assert record["latency_ms"]["embed_query"] == 2.0 and record["latency_ms"]["total"] is not None
    assert len(record["retrieved"]) == 5  # kept: the gate decision can be audited


def test_a_top_score_equal_to_the_threshold_passes_the_gate_in_both_modes():
    """The gate is `score < threshold` (AnswerQuestion); the runner's gate_fired must use the same comparison."""
    question = make_case(1)["question"]
    full = Run(retriever=ScriptedRetriever(top_scores={question: 0.5}))
    full.run([make_case(1)])
    assert full.store.records[0]["gate_fired"] is False and len(full.llm.requests) == 1
    retrieval = Run(mode="retrieval", retriever=ScriptedRetriever(top_scores={question: 0.5}))
    retrieval.run([make_case(1)])
    assert retrieval.store.records[0]["gate_fired"] is False


def test_retrieval_mode_never_calls_the_llm_and_fills_only_the_retrieval_fields():
    retriever = ScriptedRetriever(top_scores={make_case(2)["question"]: 0.3})
    run = Run(mode="retrieval", retriever=retriever)
    summary = run.run(make_cases(3))
    assert run.llm.requests == [] and len(retriever.calls) == 3 and summary.llm_requests == 0
    first, second, _ = run.store.records
    assert first["mode"] == "retrieval" and first["llm_called"] is False
    assert (first["top1_score"], first["gate_fired"], second["gate_fired"]) == (0.8, False, True)
    assert first["answer"] is None and first["insufficient"] is None and first["citations"] == []
    assert first["model_used"] is None and first["prompt_version"] is None
    assert [first["latency_ms"][stage] for stage in ("embed_query", "retrieve", "generate")] == [2.0, 3.0, None]
    assert first["latency_ms"]["total"] is not None
    assert [chunk["display_text"] for chunk in first["retrieved"]][0] == "Passage body 1."


def test_the_summary_lists_answerable_cases_refused_by_the_gate():
    retriever = ScriptedRetriever(top_scores={make_case(2)["question"]: 0.3, make_case(3)["question"]: 0.3})
    cases = [make_case(1), make_case(2), make_case(3, answerable=False)]
    summary = Run(retriever=retriever).run(cases)
    assert summary.answerable_refused_by_gate == ("Q-TEST-002",)  # case 3 is corpus-insufficient: refusing is right


# --- resume ---------------------------------------------------------------------------------------------------

def test_a_crash_after_case_three_resumes_without_regenerating_cases_one_to_three():
    crashing = ScriptedLLM("ok", "ok", "ok", RuntimeError("process died"))
    run = Run(llm=crashing)
    with pytest.raises(RuntimeError, match="process died"):
        run.run(make_cases(5))
    assert [r["case_id"] for r in run.store.records] == ["Q-TEST-001", "Q-TEST-002", "Q-TEST-003"]
    assert len(crashing.requests) == 4  # three answers and the call that died

    second = ScriptedLLM()
    run.restart(llm=second).run(make_cases(5))
    assert len(second.requests) == 2  # only cases 4 and 5
    assert len(run.store.records) == 5
    assert {key[0]: rec["status"] for key, rec in final(run.store).items()} == {f"Q-TEST-00{n}": "ok" for n in range(1, 6)}
    invocations = run.store.manifest["invocations"]
    assert len(invocations) == 2 and invocations[0]["stopped"] == "aborted" and "process died" in invocations[0]["detail"]


def test_an_error_case_is_retried_on_resume_and_the_ok_line_wins():
    flaky = ScriptedLLM("ok", "ok", "ok", LLMUnavailableError("503 after 3 attempts", model=ANSWER_MODEL, retry_count=2))
    run = Run(llm=flaky)
    first = run.run(make_cases(5))
    assert (first.ok, first.errors, first.stopped, first.remaining) == (4, 1, None, 1)  # unavailable: recorded, goes on
    assert [r["status"] for r in run.store.records] == ["ok", "ok", "ok", "error", "ok"]

    second = ScriptedLLM()
    summary = run.restart(llm=second).run(make_cases(5))
    assert len(second.requests) == 1 and (summary.skipped, summary.ok, summary.remaining) == (4, 1, 0)
    assert len(run.store.records) == 6  # append-only: the old error line stays
    assert all(record["status"] == "ok" for record in final(run.store).values()) and len(final(run.store)) == 5


def test_max_llm_calls_two_stops_after_two_and_a_resume_finishes_the_rest():
    run = Run(max_llm_calls=2)
    summary = run.run(make_cases(5))
    assert (summary.stopped, summary.ok, summary.remaining) == ("max_llm_calls", 2, 3)
    assert len(run.llm.requests) == 2 and len(run.store.records) == 2  # stopped cleanly: nothing marked as error
    second = ScriptedLLM()
    resumed = run.restart(llm=second, max_llm_calls=200).run(make_cases(5))
    assert len(second.requests) == 3 and resumed.remaining == 0 and len(run.store.records) == 5


def test_the_budget_counts_requests_including_retries_and_checks_before_each_case():
    retried = ScriptedLLM(response(answer_json(), retry_count=2))  # 3 HTTP requests for one case
    run = Run(llm=retried, max_llm_calls=3)
    summary = run.run(make_cases(3))
    assert (summary.stopped, summary.ok, summary.llm_requests) == ("max_llm_calls", 1, 3)
    assert len(retried.requests) == 1


def test_a_case_the_gate_answers_spends_no_budget():
    retriever = ScriptedRetriever(top_scores={make_case(1)["question"]: 0.2, make_case(2)["question"]: 0.2})
    run = Run(retriever=retriever, max_llm_calls=1)
    summary = run.run(make_cases(4))
    assert (summary.ok, summary.stopped, summary.llm_requests) == (3, "max_llm_calls", 1)  # 2 gated + 1 answered
    assert len(run.llm.requests) == 1


def test_retrieval_mode_ignores_the_llm_budget():
    run = Run(mode="retrieval", max_llm_calls=0)
    assert run.run(make_cases(3)).ok == 3


# --- failures -------------------------------------------------------------------------------------------------

def test_a_quota_error_stops_the_run_cleanly_and_leaves_the_other_cases_unrecorded():
    provider_body = '{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}'
    quota = LLMQuotaError("daily quota exhausted", model=ANSWER_MODEL, retry_count=0, provider_body=provider_body, daily=True)
    run = Run(llm=ScriptedLLM("ok", "ok", quota))
    summary = run.run(make_cases(5))
    assert (summary.stopped, summary.ok, summary.errors, summary.remaining) == ("quota", 2, 1, 3)
    assert "daily quota exhausted" in summary.stop_detail
    assert [r["status"] for r in run.store.records] == ["ok", "ok", "error"]  # cases 4 and 5 are NOT errors
    assert len(run.llm.requests) == 3
    [entry] = run.store.errors
    assert (entry["type"], entry["case_id"], entry["error_kind"], entry["error_model"]) == (
        "case_error", "Q-TEST-003", "quota", ANSWER_MODEL)
    assert entry["provider_body"] == provider_body
    second = ScriptedLLM()
    assert run.restart(llm=second).run(make_cases(5)).remaining == 0 and len(second.requests) == 3


def test_an_embedding_quota_error_also_stops_the_run_and_does_not_mark_the_rest():
    retriever = ScriptedRetriever(failures={make_case(2)["question"]: QuotaExhaustedError("daily embedding quota")})
    run = Run(retriever=retriever)
    summary = run.run(make_cases(4))
    assert (summary.stopped, summary.ok, summary.errors) == ("quota", 1, 1)
    failed = run.store.records[1]
    assert (failed["status"], failed["error_kind"], failed["error_model"], failed["llm_called"]) == (
        "error", "quota", None, False)
    assert len(run.store.records) == 2 and summary.llm_requests == 1


def test_an_llm_error_record_has_kind_model_and_the_retry_count_and_costs_its_requests():
    error = LLMUnavailableError("503 after 3 attempts", model=ANSWER_MODEL, retry_count=2, provider_body="{}")
    run = Run(llm=ScriptedLLM(error))
    summary = run.run([make_case(1)])
    [record] = run.store.records
    assert (record["status"], record["error_kind"], record["error_model"], record["error_type"]) == (
        "error", "unavailable", ANSWER_MODEL, "LLMUnavailableError")
    assert record["error"] == "503 after 3 attempts"
    assert (record["retry_count"], record["fallback_used"], record["llm_called"], record["answer"]) == (2, False, True, None)
    assert set(record["latency_ms"]) == set(LATENCY_STAGES) and record["latency_ms"]["total"] is not None
    assert record["retrieved"] == [] and record["top1_score"] is None and record["gate_fired"] is None
    assert summary.llm_requests == 3 and summary.errors == 1


def test_other_llm_and_generation_errors_are_recorded_and_the_run_goes_on():
    llm = ScriptedLLM(LLMRequestError("400 bad request", model=ANSWER_MODEL), GenerationError("not JSON", raw_text="{oops"))
    run = Run(llm=llm)
    summary = run.run(make_cases(3))
    assert (summary.ok, summary.errors, summary.stopped) == (1, 2, None)
    first, second, _ = run.store.records
    assert (first["error_kind"], first["error_model"], first["llm_called"]) == ("other", ANSWER_MODEL, True)
    assert (second["error_kind"], second["error_type"], second["error_model"]) == ("other", "GenerationError", None)
    assert run.store.errors[1]["raw_text"] == "{oops"  # the unusable model output is kept as evidence
    assert summary.llm_requests == 1 + 1 + 1  # 400: 1 request; unusable output: 1; the third case: 1


@pytest.mark.parametrize("error", [RetrievalError("nothing found"), EmbeddingError("embedding failed")])
def test_retrieval_and_embedding_failures_are_recorded_without_an_llm_call(error):
    run = Run(retriever=ScriptedRetriever(failures={make_case(1)["question"]: error}))
    summary = run.run(make_cases(2))
    first = run.store.records[0]
    assert (first["status"], first["error_kind"], first["llm_called"]) == ("error", "other", False)
    assert (summary.ok, summary.errors, summary.stopped, summary.llm_requests) == (1, 1, None, 1)


# --- model purity ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    response(answer_json(), fallback_used=True),
    response(answer_json(), model="some-other-model"),
])
def test_an_answer_from_the_fallback_or_another_model_aborts_the_run_and_is_not_recorded_as_ok(bad):
    run = Run(llm=ScriptedLLM("ok", bad, "ok"))
    with pytest.raises(ModelPurityError, match="Q-TEST-002"):
        run.run(make_cases(3))
    assert [r["case_id"] for r in run.store.records] == ["Q-TEST-001"]  # the contaminated answer is not a record
    [entry] = run.store.errors
    assert entry["type"] == "model_purity" and entry["case_id"] == "Q-TEST-002" and "Part says so" in entry["answer"]
    assert run.store.manifest["invocations"][0]["stopped"] == "aborted"


def test_a_gate_decision_that_disagrees_with_the_llm_call_aborts_instead_of_being_recorded():
    """If the runner's threshold and the answerer's ever drift apart, gate_fired would be wrong in every record."""
    retriever, llm = ScriptedRetriever(), ScriptedLLM()
    answerer = make_answerer(retriever, llm, 0.5)
    evaluation = RunEvaluation("run-1", make_config(), MemoryRecordStore(), retriever, answerer)
    answerer.threshold = 0.99  # the answerer's gate now stops a case (top-1 0.8) that the runner thinks passes
    with pytest.raises(EvaluationError, match="disagree"):
        evaluation.run([make_case(1)], ENVIRONMENT)


def test_the_gate_answer_is_not_a_purity_violation_although_no_model_answered():
    run = Run(retriever=ScriptedRetriever(top_scores={make_case(1)["question"]: 0.1}))
    assert run.run([make_case(1)]).ok == 1


# --- run.json and configuration ---------------------------------------------------------------------------------

def test_run_json_records_the_settings_the_environment_and_each_invocation():
    run = Run(stats=lambda: {"embedding_requests": 0, "llm_http_requests": 5})
    run.run(make_cases(5))
    manifest = run.store.manifest
    config = manifest["config"]
    assert (config["answer_model"], config["allow_fallback"], config["throttle_rpm"], config["threshold"]) == (
        ANSWER_MODEL, False, 13, 0.5)
    assert (config["prompt_version"], config["top_k"], config["overfetch"], config["freeze_tag"]) == (
        "answer_v2", 5, 10, "eval-freeze-v1")
    assert config["question_files"] == {"eval-v1.jsonl": "a" * 64, "dev-v1.jsonl": "b" * 64}
    assert (manifest["run_id"], manifest["git_commit"], manifest["git_dirty"]) == ("run-1", "abc1234", False)
    [invocation] = manifest["invocations"]
    assert (invocation["selected"], invocation["ok"], invocation["errors"], invocation["stopped"]) == (5, 5, 0, None)
    assert (invocation["llm_requests"], invocation["max_llm_calls"]) == (5, 200)
    assert invocation["embedding_requests"] == 0 and invocation["llm_http_requests"] == 5
    assert invocation["finished_at"] is not None and manifest["finished_at"] == invocation["finished_at"]
    json.dumps(manifest, allow_nan=False)


def test_resuming_with_different_settings_aborts_before_anything_is_written_or_called():
    run = Run()
    run.run(make_cases(2))
    before = json.dumps(run.store.manifest), len(run.store.records)
    for change in ({"threshold": 0.6}, {"answer_model": "another-model"}, {"prompt_version": "answer_v1"}):
        other = Run(store=run.store, config=make_config(**change), threshold=change.get("threshold", 0.5))
        with pytest.raises(RunConfigMismatch, match=next(iter(change))):
            other.run(make_cases(5))
        assert other.llm.requests == [] and other.retriever.calls == []
    assert (json.dumps(run.store.manifest), len(run.store.records)) == before


def _refused_on_resume(run, **change):
    """A resume of `run` with one changed setting: refused by run(), nothing called, nothing written."""
    before = json.dumps(run.store.manifest), len(run.store.records)
    other = Run(store=run.store, config=make_config(**change))
    with pytest.raises(RunConfigMismatch) as refusal:
        other.run(make_cases(5))
    assert other.llm.requests == [] and other.retriever.calls == []
    assert (json.dumps(run.store.manifest), len(run.store.records)) == before
    return str(refusal.value)


def test_run_refuses_to_resume_when_either_question_file_hash_differs():
    run = Run()
    run.run(make_cases(2))
    for name, other_name in (("eval-v1.jsonl", "dev-v1.jsonl"), ("dev-v1.jsonl", "eval-v1.jsonl")):
        files = {name: "c" * 64, other_name: {"eval-v1.jsonl": "a" * 64, "dev-v1.jsonl": "b" * 64}[other_name]}
        message = _refused_on_resume(run, question_files=files)
        assert "question_files" in message and "c" * 64 in message


def test_run_refuses_to_resume_when_the_prompt_file_hash_differs():
    run = Run()
    run.run(make_cases(2))
    assert "prompt_sha256" in _refused_on_resume(run, prompt_sha256="f" * 64)


def test_the_estimate_of_a_finished_run_with_different_settings_is_refused_too():
    """A finished run has nothing left to run, so only the estimate can tell the caller its settings differ."""
    run = Run()
    run.run(make_cases(2))
    other = Run(store=run.store, config=make_config(prompt_sha256="f" * 64))
    with pytest.raises(RunConfigMismatch, match="prompt_sha256"):
        other.evaluation.estimate(make_cases(2), lambda texts: [])
    assert run.store.manifest["config"]["prompt_sha256"] == "0" * 64 and len(run.store.manifest["invocations"]) == 1


def test_resuming_after_a_new_commit_is_allowed_and_records_the_new_commit_per_invocation():
    run = Run()
    run.run(make_cases(2))
    run.restart(environment=RunEnvironment("def5678", True, ("AGENTS.md",))).run(make_cases(3))
    invocations = run.store.manifest["invocations"]
    assert [i["git_commit"] for i in invocations] == ["abc1234", "def5678"]
    assert invocations[1]["git_dirty"] is True and invocations[1]["git_dirty_files"] == ["AGENTS.md"]
    assert run.store.manifest["git_commit"] == "abc1234"  # the commit the run started on


def test_a_run_config_is_validated():
    with pytest.raises(ValueError, match="fallback"):
        make_config(mode="full", allow_fallback=True)
    with pytest.raises(ValueError, match="threshold"):
        make_config(threshold=float("-inf"))
    with pytest.raises(ValueError, match="arm"):
        make_config(arm="C")
    with pytest.raises(ValueError, match="mode"):
        make_config(mode="judge")


def test_an_answerer_whose_gate_differs_from_the_configured_threshold_is_refused():
    with pytest.raises(ValueError, match="threshold"):
        Run(threshold=0.5, config=make_config(threshold=0.686))
    with pytest.raises(ValueError, match="answerer"):
        RunEvaluation("run-1", make_config(mode="full"), MemoryRecordStore(), ScriptedRetriever(), None)


# --- progress and estimate ----------------------------------------------------------------------------------------

def test_progress_lines_show_position_case_language_status_and_seconds():
    cases = [make_case(1), make_case(2, language="vi"), make_case(3)]
    run = Run(llm=ScriptedLLM("ok", LLMUnavailableError("down", model=ANSWER_MODEL), "ok"))
    run.run(cases)
    assert run.lines[0].startswith("[1/3] Q-TEST-001 en ok ") and run.lines[0].endswith("s")
    assert run.lines[1].startswith("[2/3] Q-TEST-002 vi error(unavailable) ")
    assert run.lines[2].startswith("[3/3] Q-TEST-003 en ok ")
    run.restart()
    run.lines.clear()
    run.run(cases)
    assert run.lines[0] == "[1/3] Q-TEST-001 en skipped (already ok)"
    assert run.lines[1].startswith("[2/3] Q-TEST-002 vi ok ")


def test_the_estimate_counts_uncached_embeddings_gated_cases_and_the_request_range():
    retriever = ScriptedRetriever(top_scores={make_case(2)["question"]: 0.3})  # a cached question the gate will stop
    cases = [make_case(1), make_case(2), make_case(3), make_case(4, answerable=False), make_case(5)]
    uncached = {cases[2]["question"], cases[4]["question"]}
    run = Run(retriever=retriever)
    estimate = run.evaluation.estimate(cases, lambda texts: [t for t in dict.fromkeys(texts) if t in uncached])
    assert (estimate.selected, estimate.already_ok, estimate.to_run) == (5, 0, 5)
    assert (estimate.answerable, estimate.insufficient) == (4, 1)
    assert estimate.uncached_embeddings == 2
    assert estimate.gated_known == 1
    assert (estimate.llm_requests_min, estimate.llm_requests_max) == (2, 4)  # cached non-gated: 1 and 4; uncached: 3, 5
    text = "\n".join(estimate.lines(rpd=500))
    assert "2 not cached" in text and "2 to 4" in text and "13 RPM" in text and "of 500" in text
    assert run.store.manifest is None and run.llm.requests == []  # an estimate spends and writes nothing


def test_the_estimate_skips_cases_that_are_already_ok_and_has_no_llm_requests_in_retrieval_mode():
    run = Run()
    run.run(make_cases(2))
    estimate = run.restart().evaluation.estimate(make_cases(4), lambda texts: [])
    assert (estimate.selected, estimate.already_ok, estimate.to_run) == (4, 2, 2)
    retrieval = Run(mode="retrieval").evaluation.estimate(make_cases(4), lambda texts: list(texts))
    assert (retrieval.llm_requests_min, retrieval.llm_requests_max) == (0, 0) and retrieval.uncached_embeddings == 4
