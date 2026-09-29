"""EXP-001 §1-§2: arm comparison, discordant cases, chunk facts and failure rules on made-up rows; values by hand."""
import pytest

from knowledge_assistant.application.evaluation.experiment import (
    BINARY,
    CHUNKING,
    CONTINUOUS,
    DESCRIPTIVE,
    GENERATION,
    RANKING,
    REFUSAL,
    RETRIEVAL_MISS,
    ChunkFact,
    Metric,
    chunk_facts,
    classify_failure,
    compare,
    discordant_cases,
    failure_mode_signals,
    is_failure,
    language_tag,
    paired_values,
    wording,
)
from knowledge_assistant.application.evaluation.metrics.spans import EXPECTED, ExpectedSpan


def row(case_id="Q-1", result="correct", section5=1, evidence5=1, language="en", group=None, answerable=True,
        arm="A", **retrieval):
    scores = None
    if answerable:
        scores = {"section_hit@5": section5, "evidence_hit@5": evidence5, "slot_fraction@5": float(section5),
                  "mrr": 1.0, **retrieval}
    return {"case_id": case_id, "arm": arm, "language": language, "parallel_group_id": group,
            "answerable": answerable, "retrieval": scores, "answer": {"result": result}}


def record(gate=False, top1=0.7, cited=(), **latency):
    return {"gate_fired": gate, "top1_score": top1, "citations": [{"chunk_id": c} for c in cited],
            "latency_ms": latency, "evidence": [], "retrieved": []}


def fact(rank, hit, fence=False, chunk_id=None):
    return ChunkFact(rank, chunk_id or f"c{rank}", "01", "Doc", 0.7, hit, ("S1",) if hit else (), 0, 1, (), fence, "")


# --- pairing and one comparison row ---------------------------------------------------------------------------

def test_paired_values_drop_cases_missing_in_either_arm():
    metric = Metric("accuracy", BINARY, lambda r, rec: None if r["answer"]["result"] is None else
                    int(r["answer"]["result"] == "correct"))
    rows_a = {"1": row("1"), "2": row("2", result=None), "3": row("3", result="partially_correct")}
    rows_b = {"1": row("1", arm="B"), "2": row("2", arm="B"), "3": row("3", arm="B")}
    records = {key: record() for key in rows_a}
    ids, a, b = paired_values(["1", "2", "3"], rows_a, rows_b, records, records, metric)
    assert (ids, a, b) == (["1", "3"], [1, 0], [1, 1])  # case 2 is unlabelled in A: dropped from both arms


def test_binary_row_reports_mcnemar_counts_and_cases():
    # 4 pairs: both 1, A-only (x), B-only (y, z) -> b = 1, c = 2, n = 3, p = 2 * (C(3,0)+C(3,1)) / 8 = 1.0
    result = compare(Metric("hit", BINARY, None), ["w", "x", "y", "z"], [1, 1, 0, 0], [1, 0, 1, 1])
    assert (result["a"], result["b"], result["delta"]) == (0.5, 0.75, 0.25)
    assert (result["mcnemar_b"], result["mcnemar_c"], result["p"]) == (1, 2, 1.0)
    assert (result["a_only"], result["b_only"]) == (["x"], ["y", "z"])
    assert result["wording"] == "no statistically reliable difference at n = 4"
    assert result["ci"][0] <= result["delta"] <= result["ci"][1]


def test_continuous_row_uses_wilcoxon_and_descriptive_row_is_not_tested():
    # d = B - A = +1, +2, +3, +4, +5, +6: all positive, W+ = 21, exact p = 2 / 2^6 = 0.03125
    result = compare(Metric("ms", CONTINUOUS, None), list("abcdef"), [10.0] * 6, [11.0, 12, 13, 14, 15, 16])
    assert (result["test"], result["w_plus"], result["p"]) == ("wilcoxon_exact", 21.0, 0.03125)
    assert result["wording"] == "B higher than A (p = 0.0312, n = 6)"
    descriptive = compare(Metric("embed", DESCRIPTIVE, None, "cache"), ["a", "b", "c"], [300, 350, 400], [0.1, 0.2, 0.1])
    assert (descriptive["a"], descriptive["b"], descriptive["p"], descriptive["test"]) == (350, 0.1, None, None)


def test_no_pairs_gives_an_empty_row():
    assert compare(Metric("x", BINARY, None), [], [], [])["wording"] == "no pairs"


@pytest.mark.parametrize("p, delta, text", [
    (0.05, 0.3, "no statistically reliable difference at n = 36"),  # the boundary itself names no winner
    (0.5, -0.1, "no statistically reliable difference at n = 36"),
    (0.01, -0.2, "B lower than A (p = 0.01, n = 36)"),
    (None, 0.0, "not tested"),
])
def test_wording_rule(p, delta, text):
    assert wording(p, 36, delta) == text


# --- discordant cases -----------------------------------------------------------------------------------------

def test_discordant_cases_list_label_and_retrieval_differences_only():
    keys = [f"{level}_hit@{k}{s}" for level in ("source", "section") for k in (1, 3, 5) for s in ("", ":strict")]
    keys += [f"evidence_hit@{k}" for k in (1, 3, 5)] + ["mrr:strict"]
    same = {key: 1 for key in keys}
    rows_a = {"same": row("same", **same), "label": row("label", **same), "rank": row("rank", **same),
              "unlabelled": row("unlabelled", **same), "grounded": row("grounded", **same)}
    rows_a["grounded"]["answer"]["grounded"] = False
    rows_b = {"same": row("same", arm="B", **same), "label": row("label", result="partially_correct", arm="B", **same),
              "rank": row("rank", arm="B", **{**same, "evidence_hit@1": 0}),
              "unlabelled": row("unlabelled", result=None, arm="B", **same), "grounded": row("grounded", arm="B", **same)}
    rows_b["grounded"]["answer"]["grounded"] = True
    records = {key: record() for key in rows_a}
    result = discordant_cases(sorted(rows_a), rows_a, rows_b, records, records)
    assert result == {"label": ["label correct -> partially_correct"], "rank": ["evidence_hit@1 1 -> 0"],
                      "grounded": ["grounded 0 -> 1"]}


# --- chunk facts ----------------------------------------------------------------------------------------------

def test_chunk_facts_slots_evidence_and_fence():
    spans = [ExpectedSpan("S1", EXPECTED, "01", "Doc > A", 1, 0, 100),
             ExpectedSpan("S2", EXPECTED, "02", "Doc > B", 1, 0, 100)]
    chunks = [{"rank": 1, "chunk_id": "01:x:0000", "source_id": "01", "heading_path": "Doc > A", "char_start": 50,
               "char_end": 150, "score": 0.8, "display_text": "The quote   is here. " + "z" * 300},
              {"rank": 2, "chunk_id": "03:x:0000", "source_id": "03", "heading_path": "Other", "char_start": 0,
               "char_end": 10, "score": 0.6, "display_text": "nothing"}]
    rec = {"retrieved": chunks, "answerable": True,
           "answer_points": [{"id": "P1", "required": True}, {"id": "P2", "required": True}],
           "evidence": [{"quote": "The quote is here.", "supports": ["P1"]}, {"quote": "missing", "supports": ["P2"]}]}
    first, second = chunk_facts(rec, spans, fence_cut_ids={"03:x:0000"})
    assert (first.slots_hit, first.hits_section, first.evidence_quotes_contained, first.cuts_code_fence) == (
        ("S1",), True, 1, False)  # whitespace collapsed like evidence_hit
    assert (second.slots_hit, second.hits_section, second.evidence_quotes_total, second.cuts_code_fence) == (
        (), False, 2, True)
    assert (first.points_covered, second.points_covered) == (("P1",), ())
    assert len(first.head) == 200
    assert chunk_facts(rec, None, set())[0].hits_section is None  # corpus-insufficient case: no spans


# --- failure rules --------------------------------------------------------------------------------------------

def test_success_and_unlabelled_records_are_not_failures():
    assert not is_failure(row(result="correct"))
    assert not is_failure(row(result="correct_refusal", answerable=False))
    assert not is_failure(row(result=None, section5=0))  # unlabelled: listed separately, never classified
    assert is_failure(row(result="correct", section5=0))  # a retrieval miss counts even when the answer is right
    assert classify_failure(row(), record(), [], 0.686) is None


def test_rule_1_retrieval_miss_comes_first():
    failure = classify_failure(row(result="false_refusal", section5=0), record(gate=True), [], 0.686)
    assert (failure.stage, failure.rule) == (RETRIEVAL_MISS, "section_hit@5 = 0 (slot fraction 0)")


def test_gate_false_refusal_is_refusal_with_chunking_kept_as_secondary():
    failure = classify_failure(row(result="false_refusal", evidence5=0), record(gate=True, top1=0.6246),
                               [fact(1, True)], 0.686)
    assert (failure.stage, failure.secondary) == (REFUSAL, (CHUNKING,))
    assert failure.rule == "gate: top-1 score 0.6246 < threshold 0.686"


def test_rule_2_chunking_split_evidence_or_only_hit_cuts_a_fence():
    split = classify_failure(row(result="partially_correct", evidence5=0), record(), [fact(1, True)], 0.686)
    assert (split.stage, split.secondary) == (CHUNKING, ())
    fence = classify_failure(row(result="partially_correct"), record(), [fact(1, True, fence=True), fact(2, False)],
                             0.686)
    assert fence.stage == CHUNKING and "cuts a code fence" in fence.rule
    two_hits = classify_failure(row(result="partially_correct"), record(),
                                [fact(1, True, fence=True), fact(2, True)], 0.686)
    assert two_hits.stage == GENERATION  # another section hit exists, so the fence cut is not the only hit


def test_rule_3_ranking_needs_a_cited_wrong_chunk_above_the_first_hit():
    facts = [fact(1, False), fact(2, False), fact(3, True)]
    ranked = classify_failure(row(result="partially_correct"), record(cited=("c1",)), facts, 0.686)
    assert (ranked.stage, ranked.rule) == (RANKING, "first section hit at rank 3; cites ['c1']")
    uncited = classify_failure(row(result="partially_correct"), record(cited=("c3",)), facts, 0.686)
    assert uncited.stage == GENERATION
    rank_2 = classify_failure(row(result="partially_correct"), record(cited=("c1",)), [fact(1, False), fact(2, True)],
                              0.686)
    assert rank_2.stage == GENERATION  # a first hit at rank 2 is not a ranking failure (rule needs rank >= 3)


def test_rule_4_and_5_llm_refusal_hallucination_generation():
    assert classify_failure(row(result="false_refusal"), record(), [fact(1, True)], 0.686).stage == REFUSAL
    hallucination = classify_failure(row(result="hallucination", answerable=False), record(), [], 0.686)
    assert (hallucination.stage, hallucination.rule) == (REFUSAL, "hallucination on a corpus-insufficient case")
    assert classify_failure(row(result="incorrect"), record(), [fact(1, True)], 0.686).stage == GENERATION


def test_language_tag_needs_a_passing_english_twin():
    rows = {"en": row("en", group="PG-1"), "vi": row("vi", result="partially_correct", language="vi", group="PG-1"),
            "vi2": row("vi2", result="partially_correct", language="vi", group="PG-2"),
            "en2": row("en2", result="partially_correct", group="PG-2")}
    failed = {"vi", "vi2", "en2"}
    assert language_tag("vi", rows, failed)
    assert not language_tag("vi2", rows, failed)  # the EN twin fails too: not a language effect
    assert not language_tag("en2", rows, failed)  # only VI cases get the tag


def test_failure_mode_signals_count_noise_large_docs_and_repeats():
    def chunk(source, heading):
        return {"chunk_id": f"{source}:x:{heading}", "source_id": source, "heading_path": heading}
    rec = {"expected_sources": [{"source_id": "22"}], "acceptable_alternate_sources": [],
           "retrieved": [chunk("22", "Q"), chunk("09", "Links"), chunk("13", "H"), chunk("13", "H"), chunk("22", "Q"),
                         chunk("17", "late")]}
    signals = failure_mode_signals(rec)
    assert signals["link_list_noise"] == ["09:x:Links"]
    assert signals["large_doc_off_target"] == ["13:x:H", "13:x:H"]  # rank 6 (#17) is outside the top 5
    assert signals["same_heading_repeats"] == 2  # 5 chunks, 3 distinct (source, heading) pairs
    rec["expected_sources"] = [{"source_id": "13"}, {"source_id": "09"}]
    assert failure_mode_signals(rec)["large_doc_off_target"] == []
    assert failure_mode_signals(rec)["link_list_noise"] == []
