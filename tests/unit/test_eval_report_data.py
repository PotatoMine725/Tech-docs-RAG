"""EVAL-003c: `scripts/evaluation/eval_report_data.py` - loading and scoring glue. Offline, made-up records."""
from knowledge_assistant.application.evaluation import scoring
from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan
from scripts.evaluation.eval_report_data import gate_refused_answerable, judgements_and_prompt_version, score_row
from tests.judge_fakes import make_record

SPAN = ExpectedSpan(slot="S1", role=EXPECTED, source_id="01", heading_path="Doc > Part 1", variant=0,
                    char_start=0, char_end=20)


def test_an_answerable_case_covered_by_expected_spans_scores_retrieval_and_citation():
    record = make_record(1, answerable=True, cited=(1,))
    row = score_row(record, {"Q-TEST-001": [SPAN]}, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is False
    assert row["retrieval"] is not None and row["retrieval"]["section_hit@5"] == 1
    assert row["citation"] is not None
    assert row["answer"] is not None  # full mode: answer is scored either way


def test_an_answerable_case_outside_expected_spans_skips_retrieval_and_citation_but_not_answer():
    """`expected-spans-v1.json` covers the eval split only (EVAL-003b-pre); a dev-split answerable record must
    degrade gracefully instead of raising, so a report can list it as excluded and why."""
    record = make_record(1, answerable=True, cited=(1,))
    row = score_row(record, spans_by_case={}, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is True
    assert row["retrieval"] is None
    assert row["citation"] is None
    assert row["answer"] is not None


def test_a_corpus_insufficient_case_needs_no_span_coverage():
    record = make_record(1, answerable=False, insufficient=True, cited=())
    row = score_row(record, spans_by_case={}, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is False
    assert row["retrieval"] is None  # not answerable: never scored, regardless of span coverage
    assert row["citation"] is not None  # unanswerable records still get related_citation_count
    assert row["answer"]["result"] == "correct_refusal"


def test_a_non_ok_record_is_not_scored_at_all():
    record = make_record(1, answerable=True, cited=(1,), status="error")
    row = score_row(record, {"Q-TEST-001": [SPAN]}, index=None, judgements={}, prompt_version=None)
    assert row == {"case_id": "Q-TEST-001", "arm": "A", "mode": "full", "status": "error", "language": "en",
                   "parallel_group_id": "PG-TEST-001", "answerable": True, "size_class": "tiny",
                   "difficulty": "easy", "failure_mode": "none", "retrieval": None, "duplicate_rule_changed": None,
                   "answer": None, "citation": None, "spans_unavailable": False}


def test_gate_refused_answerable_lists_case_id_arm_of_ok_answerable_gate_fired_records():
    fired = make_record(1, answerable=True, cited=())
    fired["gate_fired"] = True
    not_fired = make_record(2, answerable=True, cited=(1,))
    not_fired["gate_fired"] = False
    unanswerable_fired = make_record(3, answerable=False, insufficient=True, cited=())
    unanswerable_fired["gate_fired"] = True
    run = {"records": [fired, not_fired, unanswerable_fired]}
    assert gate_refused_answerable([run]) == ["Q-TEST-001:A"]


# --- pinned to scoring.score_record (VERIFY EVAL-003c check 2/4): every covered record is score_record's own row,
# plus spans_unavailable=False, never a hand-recomposed copy that could silently drift from it -------------------

def test_a_covered_answerable_record_equals_score_record_plus_spans_unavailable_false():
    record = make_record(1, answerable=True, cited=(1,))
    spans = {"Q-TEST-001": [SPAN]}
    row = score_row(record, spans, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is False
    expected = scoring.score_record(record, spans, None, {}, None)
    assert {k: v for k, v in row.items() if k != "spans_unavailable"} == expected


def test_an_unanswerable_record_equals_score_record_plus_spans_unavailable_false():
    record = make_record(1, answerable=False, insufficient=True, cited=())
    row = score_row(record, {}, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is False
    expected = scoring.score_record(record, {}, None, {}, None)
    assert {k: v for k, v in row.items() if k != "spans_unavailable"} == expected


def test_a_non_ok_record_equals_score_record_plus_spans_unavailable_false():
    record = make_record(1, answerable=True, cited=(1,), status="error")
    row = score_row(record, {}, index=None, judgements={}, prompt_version=None)
    assert row["spans_unavailable"] is False
    expected = scoring.score_record(record, {}, None, {}, None)
    assert {k: v for k, v in row.items() if k != "spans_unavailable"} == expected


def test_the_uncovered_branch_has_the_same_keys_as_a_covered_score_record_row():
    """Guards against `scoring.score_record` gaining a field the hand-recomposed uncovered branch would silently
    drop: a mutant adding a field to `score_record`'s row must change this set, since the covered branch (which
    spreads `score_record`'s dict directly) gains it automatically and the uncovered branch does not."""
    covered = score_row(make_record(1, answerable=True, cited=(1,)), {"Q-TEST-001": [SPAN]}, index=None,
                        judgements={}, prompt_version=None)
    uncovered = score_row(make_record(1, answerable=True, cited=(1,)), spans_by_case={}, index=None,
                          judgements={}, prompt_version=None)
    assert set(uncovered) == set(covered)


def test_judgements_and_prompt_version_is_none_when_more_than_one_version_is_present():
    assert judgements_and_prompt_version([])[1] is None
    one = [{"case_id": "c", "arm": "A", "answer_sha256": "h", "judge_prompt_version": "v1"}]
    assert judgements_and_prompt_version(one)[1] == "v1"
    two = one + [{"case_id": "c", "arm": "A", "answer_sha256": "h", "judge_prompt_version": "v2"}]
    assert judgements_and_prompt_version(two)[1] is None
