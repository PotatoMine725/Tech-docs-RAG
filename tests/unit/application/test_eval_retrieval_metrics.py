"""EVAL-003b-pre: retrieval metrics on hand-made records; every expected value is worked out by hand in the test."""
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.evaluation.metrics import retrieval
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    SOURCE,
    RankedChunk,
    any_evidence_hit_at_k,
    evidence_hit_at_k,
    mean,
    overlaps,
    reciprocal_rank,
    required_point_quotes,
    section_hit_at_k,
    slot_fraction_at_k,
    source_hit_at_k,
)
from knowledge_assistant.application.evaluation.metrics.spans import ALTERNATE, EXPECTED, ExpectedSpan

ROOT = Path(__file__).resolve().parents[3]


def span(source_id, start, end, slot="S1", role=EXPECTED, variant=1):
    return ExpectedSpan(slot, role, source_id, f"#{source_id} section", variant, start, end)


def chunk(source_id, start, end, text=""):
    return RankedChunk(source_id, start, end, text)


# --- span overlap ---------------------------------------------------------------------------------------------

def test_touching_half_open_spans_do_not_overlap():
    assert not overlaps(0, 10, 10, 20)
    assert not overlaps(10, 20, 0, 10)
    assert overlaps(0, 11, 10, 20)  # one shared character: [10, 11)


def test_section_hit_touching_chunk_is_a_miss():
    spans = [span("04", 0, 10)]
    assert section_hit_at_k([chunk("04", 10, 20)], spans, k=5) == 0
    assert section_hit_at_k([chunk("04", 9, 20)], spans, k=5) == 1


def test_section_hit_any_variant_counts():
    spans = [span("13", 0, 10, variant=1), span("13", 100, 120, variant=2)]
    assert section_hit_at_k([chunk("13", 105, 110)], spans, k=5) == 1  # inside variant 2 only
    assert section_hit_at_k([chunk("13", 50, 90)], spans, k=5) == 0  # between the variants


def test_same_offsets_in_another_document_is_a_miss():
    spans = [span("04", 0, 100)]
    assert section_hit_at_k([chunk("05", 0, 100)], spans, k=5) == 0
    assert source_hit_at_k([chunk("05", 0, 100)], spans, k=5) == 0


def test_source_hit_ignores_offsets_section_hit_does_not():
    spans = [span("04", 0, 10)]
    top = [chunk("04", 500, 600)]
    assert (source_hit_at_k(top, spans, k=5), section_hit_at_k(top, spans, k=5)) == (1, 0)


def test_hit_at_1_3_5_cut_the_ranking():
    spans = [span("04", 0, 10)]
    ranked = [chunk("09", 0, 10), chunk("09", 10, 20), chunk("04", 0, 10), chunk("09", 20, 30)]
    assert [section_hit_at_k(ranked, spans, k) for k in (1, 3, 5)] == [0, 1, 1]


# --- evidence slots: S1 = {04 expected}, S2 = {26 expected, 20 alternate} (evaluation-spec.md example) ----------

SLOT_SPANS = [
    span("04", 0, 100, slot="S1"),
    span("26", 0, 100, slot="S2"),
    span("20", 0, 100, slot="S2", role=ALTERNATE),
]


@pytest.mark.parametrize("sources, lenient, strict, fraction", [
    (("04", "20"), 1, 0, 1.0),   # the alternate satisfies S2 only under the lenient rule
    (("04", "26"), 1, 1, 1.0),
    (("20", "26"), 0, 0, 0.5),   # S1 missing under both; S2 satisfied -> 1 of 2 slots
])
def test_slot_rule_strict_and_lenient(sources, lenient, strict, fraction):
    top = [chunk(s, 10, 20) for s in sources]
    for hit in (source_hit_at_k, section_hit_at_k):
        assert hit(top, SLOT_SPANS, k=5) == lenient
        assert hit(top, SLOT_SPANS, k=5, strict=True) == strict
    assert slot_fraction_at_k(top, SLOT_SPANS, k=5) == fraction
    assert slot_fraction_at_k(top, SLOT_SPANS, k=5, level=SOURCE) == fraction


def test_alternate_counts_only_for_its_own_slot():
    spans = [span("04", 0, 100, slot="S1"), span("26", 0, 100, slot="S2"),
             span("20", 0, 100, slot="S2", role=ALTERNATE)]
    top = [chunk("20", 0, 10), chunk("26", 0, 10)]  # #20 is an S2 alternate: it cannot stand in for S1
    assert source_hit_at_k(top, spans, k=5) == 0


# --- MRR ------------------------------------------------------------------------------------------------------

def test_reciprocal_rank_hit_at_rank_3():
    ranked = [chunk("09", 0, 10), chunk("04", 200, 300), chunk("04", 5, 15)]
    assert reciprocal_rank(ranked, [span("04", 0, 10)]) == pytest.approx(1 / 3)


def test_reciprocal_rank_no_hit_is_zero():
    assert reciprocal_rank([chunk("09", 0, 10)] * 5, [span("04", 0, 10)]) == 0.0


def test_reciprocal_rank_counts_only_the_top_k():
    ranked = [chunk("09", 0, 10)] * 5 + [chunk("04", 0, 10)]
    assert reciprocal_rank(ranked, [span("04", 0, 10)], k=5) == 0.0
    assert reciprocal_rank(ranked, [span("04", 0, 10)]) == pytest.approx(1 / 6)


def test_strict_mrr_alternate_at_rank_1_expected_at_rank_3():
    spans = [span("26", 0, 100), span("20", 0, 100, role=ALTERNATE)]
    ranked = [chunk("20", 0, 10), chunk("09", 0, 10), chunk("26", 0, 10)]
    assert reciprocal_rank(ranked, spans) == 1.0
    assert reciprocal_rank(ranked, spans, strict=True) == pytest.approx(1 / 3)


def test_reciprocal_rank_hits_any_slot():
    ranked = [chunk("09", 0, 10), chunk("26", 0, 10)]
    assert reciprocal_rank(ranked, SLOT_SPANS) == 0.5  # S2 hit at rank 2, S1 never hit


def test_source_mrr():
    ranked = [chunk("09", 0, 10), chunk("04", 900, 950)]
    assert reciprocal_rank(ranked, [span("04", 0, 10)], level=SOURCE) == 0.5
    assert reciprocal_rank(ranked, [span("04", 0, 10)]) == 0.0


def test_mean_reciprocal_rank_over_cases():
    assert mean([1.0, 1 / 3, 0.0]) == pytest.approx(4 / 9)
    with pytest.raises(ValueError):
        mean([])


def test_corpus_insufficient_case_raises():
    with pytest.raises(ValueError, match="corpus-insufficient"):
        section_hit_at_k([chunk("04", 0, 10)], [], k=5)
    with pytest.raises(ValueError, match="corpus-insufficient"):
        evidence_hit_at_k([chunk("04", 0, 10, "x")], {}, k=5)
    with pytest.raises(ValueError, match="corpus-insufficient"):
        any_evidence_hit_at_k([chunk("04", 0, 10, "x")], [], k=5)
    with pytest.raises(ValueError, match="corpus-insufficient"):
        required_point_quotes({"id": "Q-X", "answerable": False, "answer_points": [], "evidence": []})


# --- evidence hit -----------------------------------------------------------------------------------------------

QUOTE = "is activated per client request (connection), so scoped services can be injected"


def eval_case(points, evidence):
    """Minimal eval-v1 record: points = [(id, required)], evidence = [(quote, supports)]."""
    return {"id": "Q-TEST", "answerable": True,
            "answer_points": [{"id": pid, "text": pid, "required": req} for pid, req in points],
            "evidence": [{"source_id": "11", "heading_path": "h", "quote": q, "supports": s} for q, s in evidence]}


def load_eval_case(case_id):
    return next(json.loads(line) for line in
                (ROOT / "data/evaluation/questions/eval-v1.jsonl").read_text(encoding="utf-8").splitlines()
                if f'"{case_id}"' in line)


def test_evidence_hit_false_when_the_quote_is_split_across_two_chunks():
    ranked = [chunk("11", 0, 30, "is activated per client request"),
              chunk("11", 30, 90, " (connection), so scoped services can be injected")]
    assert evidence_hit_at_k(ranked, {"P1": [QUOTE]}, k=5) == 0
    assert evidence_hit_at_k([chunk("11", 0, 90, "x " + QUOTE + " y")], {"P1": [QUOTE]}, k=5) == 1


def test_evidence_hit_ignores_whitespace_differences():
    text = "is  activated\nper client request (connection),\n\n  so scoped\tservices can be injected."
    assert QUOTE not in text
    assert evidence_hit_at_k([chunk("11", 0, 99, text)], {"P1": [QUOTE]}, k=5) == 1


def test_evidence_hit_respects_k():
    ranked = [chunk("09", 0, 10, "noise")] * 5 + [chunk("11", 0, 99, QUOTE)]
    assert evidence_hit_at_k(ranked, {"P1": [QUOTE]}, k=5) == 0
    assert evidence_hit_at_k(ranked, {"P1": [QUOTE]}, k=6) == 1


def test_evidence_hit_one_of_two_variant_quotes_for_a_point_is_enough():
    """Q-EVAL-023 style: P1 is supported by a long quote and a short variant; only the short one is retrieved."""
    long_p1 = "Starting in .NET 10, the default behavior is to suppress emission of diagnostics for handled exceptions."
    short_p1 = "Starting in .NET 10, diagnostics are suppressed by default for handled exceptions."
    case = eval_case([("P1", True)], [(long_p1, ["P1"]), (short_p1, ["P1"])])
    ranked = [chunk("13", 0, 99, "Intro. " + short_p1 + " More.")]
    assert required_point_quotes(case) == {"P1": [long_p1, short_p1]}
    assert evidence_hit_at_k(ranked, required_point_quotes(case), k=5) == 1


def test_evidence_hit_two_slot_case_with_one_slot_quote_found_is_a_miss():
    """Q-EVAL-029 shape: P1 is supported only by the S1 quote, P2 only by the S2 quote; only S1 is retrieved."""
    s1_quote, s2_quote = "Scoped services are created once per client request.", "Blazor circuits live per tab."
    case = eval_case([("P1", True), ("P2", True), ("P3", False)], [(s1_quote, ["P1"]), (s2_quote, ["P2"])])
    only_s1 = [chunk("11", 0, 99, s1_quote)]
    assert evidence_hit_at_k(only_s1, required_point_quotes(case), k=5) == 0
    assert any_evidence_hit_at_k(only_s1, [s1_quote, s2_quote], k=5) == 1  # the diagnostic would call it a hit
    both = only_s1 + [chunk("20", 0, 99, s2_quote)]
    assert evidence_hit_at_k(both, required_point_quotes(case), k=5) == 1


def test_evidence_hit_ignores_a_missing_optional_point_quote():
    optional_quote = "Handlers run in registration order until one returns true."
    case = eval_case([("P1", True), ("P2", False)], [(QUOTE, ["P1"]), (optional_quote, ["P2"])])
    assert required_point_quotes(case) == {"P1": [QUOTE]}
    assert evidence_hit_at_k([chunk("11", 0, 99, QUOTE)], required_point_quotes(case), k=5) == 1


def test_required_point_quotes_counts_a_quote_for_every_point_it_supports():
    case = eval_case([("P1", True), ("P2", True), ("P3", False)], [("a", ["P1"]), ("b", ["P2", "P3", "P1"])])
    assert required_point_quotes(case) == {"P1": ["a", "b"], "P2": ["b"]}


def test_required_point_quotes_raises_when_a_required_point_has_no_quote():
    with pytest.raises(ValueError, match=r"\['P2'\]"):
        required_point_quotes(eval_case([("P1", True), ("P2", True)], [("a", ["P1"])]))
    with pytest.raises(ValueError, match="no required answer point"):
        required_point_quotes(eval_case([("P1", False)], [("a", ["P1"])]))


def test_required_point_quotes_real_case_q_eval_023():
    """Real record: P1-P3 required, two quotes each (the P2/P3 quote from the alternate section counts); P4 optional."""
    points = required_point_quotes(load_eval_case("Q-EVAL-023"))
    assert list(points) == ["P1", "P2", "P3"]
    assert [len(quotes) for quotes in points.values()] == [2, 2, 2]
    assert points["P1"][1] == "Starting in .NET 10, diagnostics are suppressed by default for handled exceptions."


def test_evidence_hit_real_case_q_eval_028_no_break_space_in_source_18():
    """The #18 text has U+00A0 after 'C#'; the Arm A chunk holding the section must still count as a hit."""
    case = load_eval_case("Q-EVAL-028")
    quote = case["evidence"][0]["quote"]
    chunks = [RankedChunk.from_record(json.loads(line)) for line in
              (ROOT / "data/processed/chunks/arm-a.jsonl").read_text(encoding="utf-8").splitlines()
              if '"source_id": "18"' in line]
    holding = [c for c in chunks if "economical with regard to memory" in c.text]
    assert len(holding) == 1 and quote not in holding[0].text and " " in holding[0].text
    assert any_evidence_hit_at_k(holding, [quote], k=1) == 1
    assert evidence_hit_at_k(holding, {"P1": [quote]}, k=1) == 1


def test_whitespace_normalization_is_reused_from_validate_questions():
    filename = Path(retrieval.collapse_whitespace.__code__.co_filename).as_posix()
    assert filename.endswith("scripts/evaluation/validate_questions.py")
