"""The evaluation record schema (EVAL-003a): ground truth copied verbatim, generated fields always present."""
import copy

import pytest

from knowledge_assistant.application.common.passage import passage_hash
from knowledge_assistant.application.evaluation.records import (
    ERROR_FIELDS,
    GENERATED_FIELDS,
    GROUND_TRUTH_FIELDS,
    IDENTITY_FIELDS,
    LATENCY_STAGES,
    RECORD_FIELDS,
    TIME_FIELDS,
    assemble,
    chunk_entry,
    ground_truth,
    latest_records,
)
from knowledge_assistant.core.models import RetrievedChunk
from tests.eval_fakes import make_case
from tests.fakes import make_chunk


def test_the_schema_has_the_fields_of_the_task_prompt_and_the_addendum():
    assert set(GROUND_TRUTH_FIELDS) == {
        "question", "language", "parallel_group_id", "answerable", "expected_answer", "answer_points",
        "expected_sources", "acceptable_alternate_sources", "evidence", "acceptable_variations", "must_not_claim",
        "citation_criteria", "tags",
    }
    # the addendum's extra fields, next to the prompt's own
    assert IDENTITY_FIELDS == ("run_id", "case_id", "arm", "mode", "split", "status")
    assert {"top1_score", "gate_fired", "duplicates_dropped", "thoughts_tokens", "error_kind", "error_model"} <= set(
        RECORD_FIELDS
    )
    assert LATENCY_STAGES == ("embed_query", "retrieve", "generate", "retry_wait", "throttle_wait", "total")
    assert len(RECORD_FIELDS) == len(set(RECORD_FIELDS))
    assert RECORD_FIELDS == IDENTITY_FIELDS + ERROR_FIELDS + GROUND_TRUTH_FIELDS + GENERATED_FIELDS + TIME_FIELDS
    assert TIME_FIELDS == ("started_at", "finished_at")


def test_ground_truth_is_copied_verbatim_including_the_evidence_supports_and_is_independent_of_the_case():
    case = make_case(1)
    copied = ground_truth(case)
    assert copied == {field: case[field] for field in GROUND_TRUTH_FIELDS}
    assert copied["evidence"][0]["supports"] == ["P1"]  # the metrics need `supports`
    copied["answer_points"][0]["text"] = "changed"
    copied["tags"]["difficulty"] = "hard"
    assert case["answer_points"][0]["text"] != "changed" and case["tags"]["difficulty"] == "easy"


def test_ground_truth_of_a_case_that_lacks_a_field_is_an_error():
    case = make_case(1)
    del case["must_not_claim"]
    with pytest.raises(ValueError, match="must_not_claim"):
        ground_truth(case)


def test_assemble_returns_every_field_in_schema_order_with_defaults_for_what_was_not_generated():
    record = assemble("run-1", make_case(2), "A", "retrieval", "eval", "ok", "2026-09-27T10:00:00+00:00",
                      "2026-09-27T10:00:01+00:00", {"llm_called": False, "top1_score": 0.5})
    assert tuple(record) == RECORD_FIELDS
    assert (record["run_id"], record["case_id"], record["arm"], record["mode"], record["status"]) == (
        "run-1", "Q-TEST-002", "A", "retrieval", "ok")
    assert record["split"] == "eval"  # written from the run config, so a record says which question file it answers
    assert record["top1_score"] == 0.5 and record["answer"] is None
    # no-LLM records must count as clean in the latency table (retry_count 0, fallback False), latency_ms a full dict
    assert (record["retry_count"], record["fallback_used"], record["llm_called"]) == (0, False, False)
    assert record["latency_ms"] == dict.fromkeys(LATENCY_STAGES)
    assert record["retrieved"] == [] and record["citations"] == [] and record["error"] is None


def test_assemble_rejects_a_field_that_is_not_in_the_schema():
    with pytest.raises(ValueError, match="not_a_field"):
        assemble("run-1", make_case(1), "A", "full", "dev", "ok", "t0", "t1", {"not_a_field": 1})


def test_defaults_are_not_shared_between_records():
    first = assemble("run-1", make_case(1), "A", "full", "dev", "ok", "t0", "t1", {})
    first["retrieved"].append("x")
    first["latency_ms"]["total"] = 9.0
    second = assemble("run-1", make_case(2), "A", "full", "dev", "ok", "t0", "t1", {})
    assert second["retrieved"] == [] and second["latency_ms"]["total"] is None


def test_chunk_entry_carries_what_the_metrics_and_the_judge_need():
    chunk = make_chunk("04", 2, "Body text.", ("Doc", "Section"), char_start=10)
    hit = RetrievedChunk(chunk, rank=3, score=0.75, duplicate_chunk_ids=("04:header-1600:0009",))
    assert chunk_entry(hit) == {
        "rank": 3, "chunk_id": "04:header-1600:0002", "source_id": "04", "heading_path": "Doc > Section",
        "char_start": 10, "char_end": 20, "score": 0.75, "display_text": "Body text.",
        "passage_hash": passage_hash(chunk), "duplicate_chunk_ids": ["04:header-1600:0009"],
    }


def test_latest_records_keeps_the_last_line_per_case_arm_and_mode():
    error = {"case_id": "Q-T-1", "arm": "A", "mode": "full", "status": "error"}
    ok = {"case_id": "Q-T-1", "arm": "A", "mode": "full", "status": "ok"}
    other = {"case_id": "Q-T-2", "arm": "A", "mode": "full", "status": "error"}
    latest = latest_records([error, other, ok])
    assert latest == {("Q-T-1", "A", "full"): ok, ("Q-T-2", "A", "full"): other}
    assert list(latest) == [("Q-T-1", "A", "full"), ("Q-T-2", "A", "full")]  # first-seen order
    assert copy.deepcopy(latest) == latest
