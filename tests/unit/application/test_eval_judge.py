"""EVAL-003b §2: the LLM judge on made-up records with a scripted fake LLM (no network, no eval-set content)."""
import json

import pytest

from knowledge_assistant.application.evaluation import judge as judge_module
from knowledge_assistant.application.evaluation.judge import (
    ANSWER_CHECK,
    ANSWER_SCHEMA,
    JUDGE_ERROR,
    OK,
    REFUSAL_CHECK,
    REFUSAL_SCHEMA,
    JudgeCacheMismatch,
    JudgeConfig,
    JudgeOutputError,
    JudgeRecords,
    build_judge_prompt,
    judge_check,
    parse_template,
    parse_verdict,
    to_judge_verdict,
)
from knowledge_assistant.application.evaluation.metrics.mapping import (
    CORRECT,
    CORRECT_REFUSAL,
    HALLUCINATION,
    PARTIALLY_CORRECT,
    map_result,
)
from knowledge_assistant.core.exceptions import LLMQuotaError, LLMUnavailableError
from tests.eval_fakes import ScriptedLLM, response
from tests.judge_fakes import (
    CONFIG,
    JUDGE_MODEL,
    TEMPLATES,
    MemoryJudgementStore,
    answer_verdict,
    make_record,
    ok_response,
    refusal_verdict,
)

def judge(llm, store=None, max_llm_calls=100, config=CONFIG) -> tuple[JudgeRecords, MemoryJudgementStore]:
    store = store if store is not None else MemoryJudgementStore()
    ticks = iter(range(100_000))
    return JudgeRecords("run-1", "dev", config, TEMPLATES, llm, store, max_llm_calls,
                        clock=lambda: next(ticks) / 1000, now=lambda: "2026-09-27T00:00:00.000+00:00"), store


# --- which records get which check --------------------------------------------------------------------------

@pytest.mark.parametrize(("record", "expected"), [
    (make_record(answerable=True), ANSWER_CHECK),
    (make_record(answerable=True, insufficient=True, answer="msg", cited=()), None),  # false_refusal, no call
    (make_record(answerable=False, insufficient=True, answer="msg", cited=()), None),  # bare refusal, no call
    (make_record(answerable=False, insufficient=True, answer="msg", missing="Topic X is not covered.", cited=()),
     REFUSAL_CHECK),
    (make_record(answerable=False, insufficient=True, answer="msg", missing="  ", cited=(2,)), REFUSAL_CHECK),
    (make_record(answerable=False, insufficient=False), REFUSAL_CHECK),  # answered an unanswerable case
    (make_record(status="error"), None),
    (make_record(mode="retrieval"), None),
])
def test_judge_check_follows_the_mapping_table(record, expected):
    assert judge_check(record) == expected


# --- prompt -------------------------------------------------------------------------------------------------

def test_answer_prompt_carries_ground_truth_answer_and_full_cited_text():
    record = make_record(points=[{"id": "P1", "text": "Point one.", "required": True},
                                 {"id": "P2", "text": "Point two.", "required": False}],
                         answer="Answer [1][3].", cited=(1, 3), missing="Nothing about Z.")
    record["retrieved"][2]["display_text"] = "Full text of passage three {question} stays."
    prompt = build_judge_prompt(TEMPLATES, ANSWER_CHECK, record)
    assert "- P1 (required): Point one." in prompt and "- P2 (optional, context only): Point two." in prompt
    assert "Answer [1][3]." in prompt and "Nothing about Z." in prompt
    assert "[3] #03 — Doc > Part 3\nFull text of passage three {question} stays." in prompt  # inserted text not rescanned
    assert "Passage body 2." not in prompt  # an uncited chunk is not shown
    assert "presents_related_as_answer" not in prompt  # the refusal section is separate


def test_refusal_prompt_is_a_separate_section_with_the_note_and_related_citations():
    record = make_record(answerable=False, insufficient=True, answer="The documents do not cover this.",
                         missing="Only topic Y is described.", cited=(2,))
    prompt = build_judge_prompt(TEMPLATES, REFUSAL_CHECK, record)
    assert "presents_related_as_answer" in prompt and "insufficient: yes" in prompt
    assert "Only topic Y is described." in prompt and "Passage body 2." in prompt
    assert "required_points" not in prompt


def test_template_without_a_section_is_refused():
    with pytest.raises(ValueError, match="refusal"):
        parse_template("<!-- section: answerable -->\n" + " ".join("{%s}" % p for p in judge_module.ANSWER_PLACEHOLDERS))


def test_schemas_require_every_field():
    assert set(ANSWER_SCHEMA["required"]) == {"required_points", "contradicts_ground_truth", "unsupported_claims",
                                              "citations", "reason"}
    assert set(REFUSAL_SCHEMA["required"]) == {"presents_related_as_answer", "reason"}


# --- parsing: strict, never guessed -------------------------------------------------------------------------

TWO_POINTS = [{"id": "P1", "text": "a", "required": True}, {"id": "P2", "text": "b", "required": True},
              {"id": "P3", "text": "c", "required": False}]


def test_parse_orders_points_and_markers_as_in_the_record():
    record = make_record(points=TWO_POINTS, cited=(1, 2))
    text = answer_verdict(points=(("P2", "partial"), ("P1", "yes")), markers=((2, "no"), (1, "yes")))
    verdict = parse_verdict(ANSWER_CHECK, text, record)
    assert [p["id"] for p in verdict["required_points"]] == ["P1", "P2"]
    assert [c["marker"] for c in verdict["citations"]] == [1, 2]
    assert to_judge_verdict({"status": OK, "check": ANSWER_CHECK, "verdict": verdict}).required_points == ("yes", "partial")


@pytest.mark.parametrize("text", [
    "not json at all",
    "[1, 2]",
    answer_verdict(points=(("P1", "yes"),)),  # P2 missing
    answer_verdict(points=(("P1", "yes"), ("P2", "yes"), ("P3", "yes"))),  # optional point graded
    answer_verdict(points=(("P1", "yes"), ("P1", "yes"))),  # duplicate id, P2 missing
    answer_verdict(points=(("P1", "yes"), ("P2", "maybe"))),
    answer_verdict(points=(("P1", "yes"), ("P2", "yes")), markers=((1, "yes"),)),  # marker 2 missing
    answer_verdict(points=(("P1", "yes"), ("P2", "yes")), markers=((1, "yes"), (2, "yes"), (3, "yes"))),
    json.dumps({"required_points": [{"id": "P1", "point": "p", "covered": "yes"}, {"id": "P2", "point": "p",
                "covered": "yes"}], "unsupported_claims": [], "citations": [{"marker": 1, "supports_attached_claim": "yes"},
                {"marker": 2, "supports_attached_claim": "yes"}], "reason": "r"}),  # contradicts_ground_truth missing
    json.dumps({"required_points": [{"id": "P1", "point": "p", "covered": "yes"}, {"id": "P2", "point": "p",
                "covered": "yes"}], "contradicts_ground_truth": "false", "unsupported_claims": [],
                "citations": [{"marker": 1, "supports_attached_claim": "yes"}, {"marker": 2,
                "supports_attached_claim": "yes"}], "reason": "r"}),  # a string, not a boolean
])
def test_malformed_or_incomplete_answer_verdicts_raise(text):
    record = make_record(points=TWO_POINTS, cited=(1, 2))
    with pytest.raises(JudgeOutputError):
        parse_verdict(ANSWER_CHECK, text, record)


@pytest.mark.parametrize("text", ['{"reason": "r"}', '{"presents_related_as_answer": "no", "reason": "r"}',
                                  '{"presents_related_as_answer": false}'])
def test_malformed_refusal_verdicts_raise(text):
    with pytest.raises(JudgeOutputError):
        parse_verdict(REFUSAL_CHECK, text, make_record(answerable=False))


# --- the run: cache, errors, model, budget ------------------------------------------------------------------

def test_one_call_per_record_temperature_0_and_the_check_schema():
    records = [make_record(1), make_record(2, answerable=False, insufficient=False)]
    llm = ScriptedLLM(ok_response(answer_verdict()), ok_response(refusal_verdict(False)))
    summary = judge(llm)[0].run(records)
    assert (summary.ok, summary.errors, summary.llm_requests) == (2, 0, 2)
    assert [r.response_schema for r in llm.requests] == [ANSWER_SCHEMA, REFUSAL_SCHEMA]
    assert all(r.temperature == 0.0 and r.max_output_tokens == 2048 for r in llm.requests)


def test_cache_prevents_a_second_call():
    records = [make_record(1)]
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict())))
    runner.run(records)
    again = ScriptedLLM()
    summary = judge(again, store)[0].run(records)
    assert again.requests == [] and (summary.cached, summary.llm_requests, summary.remaining) == (1, 0, 0)
    assert len(store.lines) == 1


@pytest.mark.parametrize("change", ["answer", "arm", "prompt_version", "case_id"])
def test_every_cache_key_component_forces_a_new_call(change):
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict())))
    runner.run([make_record(1)])
    record, config = make_record(1), CONFIG
    if change == "answer":
        record["answer"] = "Part 1 says so, in other words [1]."
    elif change == "arm":
        record["arm"] = "B"
    elif change == "case_id":
        record["case_id"] = "Q-TEST-999"
    else:
        config = JudgeConfig(JUDGE_MODEL, "judge_v2", "b" * 64, 2048)
    llm = ScriptedLLM(ok_response(answer_verdict()))
    judge(llm, store, config=config)[0].run([record])
    assert len(llm.requests) == 1


def test_same_key_with_another_prompt_hash_or_model_refuses_to_run():
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict())))
    runner.run([make_record(1)])
    for config in (JudgeConfig(JUDGE_MODEL, "judge_v1", "b" * 64, 2048), JudgeConfig("other-model", "judge_v1", "a" * 64, 2048)):
        llm = ScriptedLLM()
        with pytest.raises(JudgeCacheMismatch):
            judge(llm, store, config=config)[0].run([make_record(1)])
        assert llm.requests == []


def test_malformed_judge_json_is_a_judge_error_and_is_retried_next_time():
    runner, store = judge(ScriptedLLM(ok_response("{not json")))
    summary = runner.run([make_record(1)])
    line = store.lines[0]
    assert (summary.ok, summary.errors, summary.remaining) == (0, 1, 1)
    assert (line["status"], line["verdict"], line["error_type"], line["raw_text"]) == (JUDGE_ERROR, None,
                                                                                         "JudgeOutputError", "{not json")
    llm = ScriptedLLM(ok_response(answer_verdict()))
    judge(llm, store)[0].run([make_record(1)])
    assert len(llm.requests) == 1 and store.lines[-1]["status"] == OK


def test_a_judgement_from_another_model_is_rejected():
    runner, store = judge(ScriptedLLM(response(answer_verdict(), model="some-other-model")))
    runner.run([make_record(1)])
    assert (store.lines[0]["status"], store.lines[0]["error_type"], store.lines[0]["verdict"]) == (
        JUDGE_ERROR, "JudgeModelMismatch", None)


def test_a_fallback_judgement_is_rejected():
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict(), fallback_used=True)))
    runner.run([make_record(1)])
    assert store.lines[0]["error_type"] == "JudgeModelMismatch"


def test_provider_error_is_recorded_and_the_run_goes_on_quota_stops_it():
    records = [make_record(1), make_record(2), make_record(3)]
    llm = ScriptedLLM(LLMUnavailableError("503", retry_count=2), LLMQuotaError("429 daily", daily=True),
                      ok_response(answer_verdict()))
    runner, store = judge(llm)
    summary = runner.run(records)
    assert (summary.errors, summary.stopped, summary.llm_requests, summary.remaining) == (2, "quota", 3 + 1, 3)
    assert [line["error_kind"] for line in store.lines] == ["unavailable", "quota"]
    assert len(llm.requests) == 2  # the third record was never sent


def test_budget_counts_requests_and_stops_before_the_next_call():
    records = [make_record(n) for n in (1, 2, 3)]
    llm = ScriptedLLM(ok_response(answer_verdict(), retry_count=1), ok_response(answer_verdict()))
    summary = judge(llm, max_llm_calls=2)[0].run(records)
    assert (summary.ok, summary.llm_requests, summary.stopped, summary.remaining) == (1, 2, "max_llm_calls", 2)


def test_judgement_line_records_tokens_latency_and_the_key():
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict(), throttle_wait_ms=5.0)))
    runner.run([make_record(1)])
    line = store.lines[0]
    assert (line["prompt_tokens"], line["output_tokens"], line["thoughts_tokens"]) == (100, 20, 7)
    assert line["latency_ms"]["generate"] == 50.0 and line["latency_ms"]["throttle_wait"] == 5.0
    assert line["latency_ms"]["total"] == pytest.approx(1.0)  # one fake-clock tick
    assert (line["judge_model"], line["judge_prompt_version"], line["check"], line["split"]) == (
        JUDGE_MODEL, "judge_v1", ANSWER_CHECK, "dev")
    assert line["answer_sha256"] == judge_module.answer_sha256(make_record(1))


def test_plan_counts_calls_cached_and_no_call_records():
    records = [make_record(1), make_record(2, answerable=False, insufficient=True, answer="m", cited=()),
               make_record(3, status="error")]
    runner, store = judge(ScriptedLLM(ok_response(answer_verdict())))
    plan = runner.plan(records)
    assert (plan.need_judge, plan.cached, plan.to_call, plan.no_call, plan.not_scored) == (1, 0, 1, 1, 1)
    runner.run(records)
    assert runner.plan(records).cached == 1


# --- verdict → label (the table stays in code) --------------------------------------------------------------

def test_judged_records_map_to_labels():
    record = make_record(points=TWO_POINTS, cited=(1,))
    answer = to_judge_verdict({"status": OK, "check": ANSWER_CHECK, "verdict": parse_verdict(
        ANSWER_CHECK, answer_verdict(points=(("P1", "yes"), ("P2", "no"))), record)})
    assert map_result(True, False, judge=answer) == PARTIALLY_CORRECT
    full = to_judge_verdict({"status": OK, "check": ANSWER_CHECK, "verdict": parse_verdict(
        ANSWER_CHECK, answer_verdict(points=(("P1", "yes"), ("P2", "yes"))), record)})
    assert map_result(True, False, judge=full) == CORRECT
    for presents, label in ((True, HALLUCINATION), (False, CORRECT_REFUSAL)):
        verdict = to_judge_verdict({"status": OK, "check": REFUSAL_CHECK,
                                    "verdict": parse_verdict(REFUSAL_CHECK, refusal_verdict(presents), make_record())})
        assert map_result(False, True, has_related_note=True, judge=verdict) == label


def test_a_judge_error_line_has_no_verdict_to_map():
    with pytest.raises(ValueError):
        to_judge_verdict({"status": JUDGE_ERROR, "check": ANSWER_CHECK, "verdict": None})
