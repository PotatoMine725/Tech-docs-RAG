"""Runner records go straight into the EVAL-003b-pre functions, with no adapter (EVAL-003a, owner addendum 2026-09-27).

This resolves 09b's open items "latency record shape" and "RankedChunk adapter": the records are written by the real
RunEvaluation through the real JsonlRecordStore, read back from disk, and handed to the metric functions untouched.
"""
import pytest

from knowledge_assistant.application.evaluation.metrics.latency import summarize_latency
from knowledge_assistant.application.evaluation.metrics.mapping import (
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    map_result,
)
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    RankedChunk,
    evidence_hit_at_k,
    reciprocal_rank,
    required_point_quotes,
    section_hit_at_k,
    slot_fraction_at_k,
    source_hit_at_k,
)
from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan
from knowledge_assistant.application.evaluation.records import latest_records
from knowledge_assistant.application.evaluation.run_evaluation import RunEnvironment, RunEvaluation
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore
from tests.eval_fakes import (
    ENVIRONMENT,
    ScriptedLLM,
    ScriptedRetriever,
    answer_json,
    make_answerer,
    make_case,
    make_config,
    response,
)


def _run(tmp_path, cases, llm=None, retriever=None, mode="full"):
    retriever = retriever or ScriptedRetriever()
    store = JsonlRecordStore(tmp_path / "run-1", redact=lambda text: text)
    answerer = make_answerer(retriever, llm or ScriptedLLM(), 0.5)
    RunEvaluation("run-1", make_config(mode=mode), store, retriever, answerer).run(cases, ENVIRONMENT)
    return JsonlRecordStore(tmp_path / "run-1", redact=lambda text: text).read_records()  # what the files hold


def _spans(case_number: int) -> list[ExpectedSpan]:
    """The expected span of made-up case n: its own passage (chunk n covers [0, len(text)) of source n)."""
    return [ExpectedSpan("S1", EXPECTED, f"{case_number:02d}", f"Doc > Part {case_number}", 1, 0,
                         len(f"Passage body {case_number}."))]


def test_records_from_disk_go_into_the_latency_summary_as_they_are(tmp_path):
    question_2 = make_case(2)["question"]
    retriever = ScriptedRetriever(top_scores={question_2: 0.3})  # case 2: the gate answers, no LLM call
    llm = ScriptedLLM("ok", "ok", response(answer_json(), retry_count=1, retry_wait_ms=1200.0), "ok")
    records = _run(tmp_path, [make_case(n) for n in (1, 2, 3, 4)], llm=llm, retriever=retriever)

    summary = summarize_latency(records)
    assert summary["main"]["count"] == 3  # cases 1, 2 (gate: retry_count 0, no fallback) and 4
    assert summary["retried_or_fallback"]["count"] == 1  # case 3 needed a retry
    main = summary["main"]["stages"]
    assert main["total"]["n"] == 3 and main["embed_query"]["n"] == 3 and main["retrieve"]["n"] == 3
    assert main["generate"]["n"] == 2  # the gate case has no generate stage: skipped, not counted as zero
    assert summary["retried_or_fallback"]["stages"]["generate"]["n"] == 1


def test_retrieval_mode_records_go_into_the_latency_summary_too(tmp_path):
    records = _run(tmp_path, [make_case(n) for n in (1, 2, 3)], mode="retrieval")
    summary = summarize_latency(records)
    assert summary["main"]["count"] == 3 and summary["retried_or_fallback"]["count"] == 0
    assert summary["main"]["stages"]["generate"]["n"] == 0 and summary["main"]["stages"]["total"]["n"] == 3


def test_a_record_feeds_the_retrieval_metrics_without_an_adapter(tmp_path):
    hit, miss = _run(tmp_path, [make_case(1), make_case(9)])  # the scripted retriever always returns passages 1-5
    for record, expected in ((hit, 1), (miss, 0)):
        number = int(record["case_id"][-3:])
        chunks = [RankedChunk.from_record(entry) for entry in record["retrieved"]]  # straight from the record
        spans = _spans(number)
        quotes = required_point_quotes(record)  # the record itself, not the dataset case
        assert quotes == {"P1": [f"Passage body {number}."]}
        assert evidence_hit_at_k(chunks, quotes, 5) == expected
        assert section_hit_at_k(chunks, spans, 5) == expected and source_hit_at_k(chunks, spans, 5) == expected
        assert slot_fraction_at_k(chunks, spans, 5) == float(expected)
        assert reciprocal_rank(chunks, spans, 5) == (1.0 if expected else 0.0)


def test_required_point_quotes_names_the_case_for_a_record_that_cannot_be_scored(tmp_path):
    [record] = _run(tmp_path, [make_case(1, answerable=False)])
    with pytest.raises(ValueError, match="Q-TEST-001"):  # a record has `case_id`, the dataset case has `id`
        required_point_quotes(record)


def test_records_feed_the_result_mapping_for_the_cases_the_gate_answered(tmp_path):
    question_1, question_2 = make_case(1)["question"], make_case(2)["question"]
    retriever = ScriptedRetriever(top_scores={question_1: 0.2, question_2: 0.2})
    answerable_gated, unanswerable_gated = _run(tmp_path, [make_case(1), make_case(2, answerable=False)],
                                                retriever=retriever)
    for record, expected in ((answerable_gated, FALSE_REFUSAL), (unanswerable_gated, CORRECT_REFUSAL)):
        assert map_result(record["answerable"], record["insufficient"],
                          has_related_note=bool(record["missing_information"]),
                          has_related_citations=bool(record["citations"])) == expected


def test_the_last_line_per_case_is_what_the_metrics_should_read(tmp_path):
    """After a retry, records.jsonl holds the error line and the ok line; `latest_records` returns the ok one."""
    retriever = ScriptedRetriever()
    store = JsonlRecordStore(tmp_path / "run-1", redact=lambda text: text)
    from knowledge_assistant.core.exceptions import LLMUnavailableError

    def run(llm):
        answerer = make_answerer(retriever, llm, 0.5)
        RunEvaluation("run-1", make_config(), store, retriever, answerer).run([make_case(1)], RunEnvironment("abc", False))

    run(ScriptedLLM(LLMUnavailableError("down", model="test-answer-model")))
    run(ScriptedLLM())
    records = store.read_records()
    assert [r["status"] for r in records] == ["error", "ok"]
    assert [r["status"] for r in latest_records(records).values()] == ["ok"]
