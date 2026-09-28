"""EVAL-003b §4: per-record scores and summaries on made-up records; every expected value is worked out by hand."""
import json

import pytest

from knowledge_assistant.application.evaluation.judge import (
    ANSWER_CHECK,
    JUDGE_ERROR,
    OK,
    REFUSAL_CHECK,
    answer_sha256,
    latest_judgements,
    parse_verdict,
)
from knowledge_assistant.application.evaluation.metrics.spans import ALTERNATE, EXPECTED, ExpectedSpan
from knowledge_assistant.application.evaluation.scoring import (
    CITATION_MISSING,
    CORRECT_EVIDENCE,
    CORRECT_SOURCE_WRONG_EVIDENCE,
    UNSUPPORTED_CITATION,
    answer_scores,
    breakdown,
    citation_scores,
    cost_summary,
    estimate_usd,
    retrieval_scores,
    score_record,
    summarize,
    summarize_answers,
    summarize_citations,
    summarize_judge_latency,
    summarize_retrieval,
)
from tests.judge_fakes import JUDGE_MODEL, answer_verdict, make_record, refusal_verdict

# Case Q-TEST-001 (made up): one slot, expected section #01 [0, 20); chunk n is #0n [0, 20) with text "Passage body n."
SPANS = [ExpectedSpan("S1", EXPECTED, "01", "Doc > Part 1", 1, 0, 20)]
SPANS_BY_CASE = {"Q-TEST-001": SPANS, "Q-TEST-002": [ExpectedSpan("S1", EXPECTED, "02", "Doc > Part 2", 1, 0, 20)]}


def judgement(record: dict, text: str, check: str = ANSWER_CHECK, status: str = OK) -> dict:
    return {"case_id": record["case_id"], "arm": record["arm"], "answer_sha256": answer_sha256(record),
            "judge_prompt_version": "judge_v1", "check": check, "status": status,
            "verdict": parse_verdict(check, text, record) if status == OK else None}


# --- citations (OD-12: span check and judge support check, separately) ---------------------------------------

def test_citation_precision_support_and_both_classes():
    record = make_record(1, cited=(1, 2), answer="A [1]. B [2].")
    j = judgement(record, answer_verdict(markers=((1, "no"), (2, "yes"))))
    scores = citation_scores(record, SPANS, None, j)
    # chunk 1 = #01 overlaps the expected span; chunk 2 = #02 is another document
    assert (scores["source_precision"], scores["section_precision"]) == (0.5, 0.5)
    assert scores["support_rate"] == 0.5  # marker 2 judged yes
    assert (scores["auto_class"], scores["judge_class"]) == (CORRECT_EVIDENCE, CORRECT_EVIDENCE)


def test_right_document_wrong_section_is_correct_source_wrong_evidence():
    record = make_record(1, cited=(1,))
    record["retrieved"][0].update(char_start=100, char_end=120)  # #01, but outside [0, 20)
    j = judgement(record, answer_verdict(markers=((1, "partial"),)))
    scores = citation_scores(record, SPANS, None, j)
    assert (scores["source_precision"], scores["section_precision"], scores["support_rate"]) == (1.0, 0.0, 0.0)
    assert (scores["auto_class"], scores["judge_class"]) == (CORRECT_SOURCE_WRONG_EVIDENCE, CORRECT_SOURCE_WRONG_EVIDENCE)


def test_span_check_and_judge_check_can_disagree():
    record = make_record(1, cited=(2,), answer="A [1].")  # cites #02 only
    j = judgement(record, answer_verdict(markers=((2, "yes"),)))  # the judge says the passage supports the claim
    scores = citation_scores(record, SPANS, None, j)
    assert (scores["auto_class"], scores["judge_class"]) == (UNSUPPORTED_CITATION, CORRECT_EVIDENCE)


def test_no_citation_is_citation_missing_with_no_precision():
    record = make_record(1, cited=(), answer="A.")
    scores = citation_scores(record, SPANS, None, judgement(record, answer_verdict(markers=())))
    assert (scores["citation_present"], scores["source_precision"], scores["support_rate"]) == (False, None, None)
    assert (scores["auto_class"], scores["judge_class"]) == (CITATION_MISSING, CITATION_MISSING)


def test_a_duplicate_of_the_cited_chunk_counts_for_section_precision():
    record = make_record(1, cited=(2,), answer="A [1].")
    record["retrieved"][1]["duplicate_chunk_ids"] = ["01:header-1600:0009"]
    scores = citation_scores(record, SPANS, {"01:header-1600:0009": ("01", 5, 15)}, None)
    assert (scores["section_precision"], scores["auto_class"], scores["judge_class"]) == (1.0, CORRECT_EVIDENCE, None)
    assert scores["source_precision"] == 0.0  # source level: the cited chunk's own document (#02), what the user sees


def test_related_citations_of_an_insufficient_answer_are_only_counted():
    record = make_record(1, answerable=False, insufficient=True, answer="msg", missing="X is not covered.", cited=(1, 2))
    scores = citation_scores(record, None, None, None)
    assert scores["related_citation_count"] == 2
    assert (scores["citation_present"], scores["auto_class"], scores["answered"]) == (None, None, False)


def test_citation_summary_excludes_insufficient_records_and_counts_related_citations():
    answered = make_record(1, cited=(1,))
    refused = make_record(2, answerable=False, insufficient=True, answer="msg", missing="n", cited=(1, 2, 3))
    judgements = latest_judgements([
        {**judgement(answered, answer_verdict(markers=((1, "yes"),))), "judge_model": JUDGE_MODEL},
    ])
    rows = [score_record(r, SPANS_BY_CASE, None, judgements, "judge_v1") for r in (answered, refused)]
    summary = summarize_citations(rows)
    assert summary["answered"] == 1 and summary["related_citation_count"] == 3
    assert summary["presence_rate"]["value"] == 1.0 and summary["support_rate"]["value"] == 1.0
    assert summary["auto_class"][CORRECT_EVIDENCE] == 1 and summary["judge_class"][CORRECT_EVIDENCE] == 1


# --- denominators: an unlabelled record stays in citation-presence numbers, not judge-dependent ones -----------
# (evaluation-spec.md § Answer and citation scoring, 2026-09-28 fix: the old prose said unlabelled records are
# excluded from every denominator; `summarize_citations` never filters by label, so that was wrong.)

def test_an_unlabelled_answered_record_stays_in_the_citation_denominator_but_not_accuracy():
    ok = make_record(1, cited=(1,))
    err = make_record(2, cited=(1,))
    judgements = latest_judgements([
        judgement(ok, answer_verdict(markers=((1, "yes"),))),
        judgement(err, "", status=JUDGE_ERROR),
    ])
    rows = [score_record(r, SPANS_BY_CASE, None, judgements, "judge_v1") for r in (ok, err)]
    summary = summarize(rows)
    assert summary["answer"]["unlabelled"] == ["Q-TEST-002:A"]
    assert summary["answer"]["accuracy"]["n"] == 1
    assert summary["answer"]["groundedness_rate"]["n"] == 1
    assert summary["citation"]["answered"] == 2
    assert summary["citation"]["presence_rate"] == {"n": 2, "count": 2, "value": 1.0}


# --- answer labels ------------------------------------------------------------------------------------------

def test_missing_or_failed_judgement_leaves_the_record_unlabelled():
    record = make_record(1)
    assert answer_scores(record, None)["result"] is None
    failed = answer_scores(record, judgement(record, "", status=JUDGE_ERROR))
    assert (failed["result"], failed["judge_status"]) == (None, JUDGE_ERROR)


def test_bare_refusal_and_answerable_refusal_need_no_judgement():
    bare = make_record(1, answerable=False, insufficient=True, answer="msg", cited=())
    refused = make_record(2, answerable=True, insufficient=True, answer="msg", cited=())
    assert answer_scores(bare, None)["result"] == "correct_refusal"
    assert answer_scores(refused, None)["result"] == "false_refusal"


def test_answer_scores_from_a_judgement():
    points = [{"id": "P1", "text": "a", "required": True}, {"id": "P2", "text": "b", "required": True},
              {"id": "P3", "text": "c", "required": True}, {"id": "P4", "text": "d", "required": False}]
    record = make_record(1, points=points)
    j = judgement(record, answer_verdict(points=(("P1", "yes"), ("P2", "partial"), ("P3", "no")),
                                         unsupported=("It is fast.",)))
    scores = answer_scores(record, j)
    assert (scores["result"], scores["points_covered"], scores["grounded"]) == ("partially_correct", 0.5, False)


def test_refusal_check_labels_without_groundedness():
    record = make_record(1, answerable=False, insufficient=False, answer="Use X [1].")
    scores = answer_scores(record, judgement(record, refusal_verdict(True), check=REFUSAL_CHECK))
    assert (scores["result"], scores["grounded"], scores["points_covered"]) == ("hallucination", None, None)


def _row(result, answerable, check=ANSWER_CHECK, grounded=True, covered=1.0, language="en", arm="A", group=None):
    return {"case_id": f"Q-{result}", "arm": arm, "status": "ok", "language": language, "parallel_group_id": group,
            "answerable": answerable, "size_class": "small", "difficulty": "easy", "failure_mode": "none",
            "retrieval": None, "duplicate_rule_changed": None, "citation": None,
            "answer": {"check": check if answerable and result not in ("false_refusal",) else REFUSAL_CHECK,
                       "result": result, "grounded": grounded, "points_covered": covered}}


def test_answer_and_refusal_rates():
    rows = [_row("correct", True, covered=1.0), _row("partially_correct", True, covered=0.5, grounded=False),
            _row("incorrect", True, covered=0.0), _row("false_refusal", True, grounded=None, covered=None),
            _row("correct_refusal", False), _row("hallucination", False), _row(None, True)]
    summary = summarize_answers(rows)
    assert summary["accuracy"] == {"n": 4, "count": 1, "value": 0.25}
    assert summary["lenient_accuracy"]["value"] == 0.5
    assert summary["false_refusal_rate"]["value"] == 0.25
    assert (summary["correct_refusal_rate"]["value"], summary["hallucination_rate"]["value"]) == (0.5, 0.5)
    assert summary["groundedness_rate"] == {"n": 3, "count": 2, "value": pytest.approx(2 / 3)}
    assert summary["points_covered_mean"]["value"] == pytest.approx(0.5)  # (1 + 0.5 + 0) / 3
    assert summary["unlabelled"] == ["Q-None:A"]


def test_runner_error_records_are_listed_not_silently_dropped():
    rows = [score_record(make_record(1, answerable=False, insufficient=True, answer="m", cited=()), SPANS_BY_CASE, None,
                         {}, "judge_v1"),
            score_record(make_record(2, status="error"), SPANS_BY_CASE, None, {}, "judge_v1")]
    summary = summarize_answers(rows)
    assert summary["runner_errors"] == ["Q-TEST-002:A"] and summary["records"] == 1


def test_breakdowns_by_language_arm_and_parallel_subset():
    rows = [_row("correct", True, language="en", group="PG-1"), _row("incorrect", True, language="vi", group="PG-1"),
            _row("correct", True, language="vi", arm="B")]
    result = breakdown(rows, summarize_answers)
    assert result["overall"]["accuracy"]["value"] == pytest.approx(2 / 3)
    assert result["language"]["vi"]["accuracy"]["value"] == 0.5
    assert result["arm"]["B"]["accuracy"]["value"] == 1.0
    assert result["parallel"]["accuracy"] == {"n": 2, "count": 1, "value": 0.5}
    assert set(result) == {"overall", "parallel", "language", "arm", "size_class", "difficulty", "failure_mode"}


# --- retrieval rows -----------------------------------------------------------------------------------------

def test_retrieval_scores_lenient_strict_and_diagnostics():
    record = make_record(1)
    # rank 1 = #01 [0, 20) holds the quote "Passage body 1." (make_case: evidence quote of P1)
    spans = SPANS + [ExpectedSpan("S1", ALTERNATE, "02", "Doc > Part 2", 1, 0, 20)]
    record["retrieved"] = [record["retrieved"][1], record["retrieved"][0], record["retrieved"][2]]  # #02, #01, #03
    scores = retrieval_scores(record, spans, None)
    assert (scores["section_hit@1"], scores["section_hit@1:strict"]) == (1, 0)  # alternate #02 at rank 1
    assert (scores["mrr"], scores["mrr:strict"]) == (1.0, 0.5)
    assert (scores["evidence_hit@1"], scores["evidence_hit@3"]) == (0, 1)
    assert scores["evidence_hit_via_alternate_only@5"] == 0


def test_retrieval_summary_counts_duplicate_rule_changes():
    record = make_record(2)  # expected #02 [0, 20)
    record["retrieved"] = [record["retrieved"][0]]  # only #01 is retrieved ...
    record["retrieved"][0]["duplicate_chunk_ids"] = ["02:header-1600:0000"]  # ... whose dropped copy is #02
    record["retrieved"][0]["display_text"] = "Passage body 2."
    row = score_record(record, SPANS_BY_CASE, {"02:header-1600:0000": ("02", 0, 20)}, {}, "judge_v1")
    assert row["retrieval"]["section_hit@5"] == 1
    summary = summarize_retrieval([row])
    assert summary["duplicate_rule_changed"]["count"] == 1 and summary["duplicate_rule_changed"]["cases"] == ["Q-TEST-002:A"]


def test_score_record_needs_spans_for_an_answerable_case():
    with pytest.raises(ValueError, match="no expected spans"):
        score_record(make_record(3), SPANS_BY_CASE, None, {}, "judge_v1")


def test_score_record_refuses_unresolved_duplicates():
    record = make_record(1)
    record["retrieved"][0]["duplicate_chunk_ids"] = ["09:header-1600:0000"]
    with pytest.raises(ValueError, match="duplicate"):
        score_record(record, SPANS_BY_CASE, None, {}, "judge_v1")


# --- latency and cost ---------------------------------------------------------------------------------------

def _line(model=JUDGE_MODEL, prompt=1000, output=100, thoughts=None, retry=0, generate=10.0, total=12.0):
    return {"case_id": "Q", "model_used": model, "prompt_tokens": prompt, "output_tokens": output,
            "thoughts_tokens": thoughts, "retry_count": retry, "fallback_used": False,
            "latency_ms": {"generate": generate, "total": total}}


def test_judge_latency_separates_retried_calls():
    lines = [_line(generate=10.0), _line(generate=30.0), _line(generate=20.0), _line(retry=1, generate=500.0),
             {**_line(), "model_used": None, "retry_count": None}]
    summary = summarize_judge_latency(lines)
    assert summary["main"]["count"] == 3 and summary["main"]["stages"]["generate"]["p50"] == 20.0
    assert summary["retried_or_fallback"]["count"] == 1


PRICING = {"source": {"url": "u"}, "models": {JUDGE_MODEL: {"input_per_1m_usd": 0.30, "output_per_1m_usd": 2.50},
                                              "free-model": {"input_per_1m_usd": None, "output_per_1m_usd": None}}}


def test_cost_estimate_prices_thinking_tokens_as_output():
    tokens = {"models": [JUDGE_MODEL], "prompt_tokens": 2000, "output_tokens": 150, "thoughts_tokens": 50,
              "calls_without_thoughts_tokens": 0}
    assert estimate_usd(tokens, PRICING)["usd"] == pytest.approx((2000 * 0.30 + 200 * 2.50) / 1e6)  # 0.0011


def test_cost_estimate_is_none_when_the_price_is_not_available_or_models_mix():
    tokens = {"models": ["free-model"], "prompt_tokens": 1, "output_tokens": 1, "thoughts_tokens": 0,
              "calls_without_thoughts_tokens": 0}
    assert estimate_usd(tokens, PRICING) == {"usd": None, "reason": "price for free-model not available"}
    assert estimate_usd({**tokens, "models": [JUDGE_MODEL, "free-model"]}, PRICING)["usd"] is None


def test_cost_summary_per_stage_and_per_question():
    records = [{**make_record(n), "model_used": JUDGE_MODEL, "prompt_tokens": 1000, "output_tokens": 100,
                "thoughts_tokens": None} for n in (1, 2)]
    records.append(make_record(3, answerable=False, insufficient=True, answer="m", cited=()))  # gate: no LLM call
    records[2]["llm_called"] = False
    cost = cost_summary(records, [_line(prompt=3000, output=300, thoughts=20)], PRICING)
    answer, judge = cost["stages"]["answer"], cost["stages"]["judge"]
    assert (answer["calls"], answer["prompt_tokens"], answer["per_question"]["output_tokens"]) == (2, 2000, 100.0)
    assert answer["calls_without_thoughts_tokens"] == 2 and "no thinking-token count" in answer["estimate"]["reason"]
    assert answer["estimate"]["usd"] == pytest.approx((2000 * 0.30 + 200 * 2.50) / 1e6)
    assert judge["estimate"]["usd"] == pytest.approx((3000 * 0.30 + 320 * 2.50) / 1e6)
    assert "free tier" in cost["note"]


def test_per_question_tokens_count_each_arm_as_its_own_call():
    """One case answered on both arms is 2 calls: 100 output tokens per call, not 200 per distinct case id."""
    records = [{**make_record(1, arm=arm), "model_used": JUDGE_MODEL, "prompt_tokens": 1000, "output_tokens": 100,
                "thoughts_tokens": None} for arm in ("A", "B")]
    answer = cost_summary(records, [], PRICING)["stages"]["answer"]
    assert (answer["calls"], answer["per_question"]["output_tokens"]) == (2, 100.0)


def test_real_pricing_file_is_cited_and_never_guesses():
    from knowledge_assistant.config import get_pricing_path

    pricing = json.loads(get_pricing_path().read_text(encoding="utf-8"))
    assert pricing["source"]["url"].startswith("https://ai.google.dev/") and pricing["source"]["retrieved"]
    for model, price in pricing["models"].items():
        if price["input_per_1m_usd"] is None:
            assert price["output_per_1m_usd"] is None and "not available" in price["status"], model
