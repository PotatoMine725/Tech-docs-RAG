"""EVAL-003b-pre: retrieval metrics on hand-made records; every expected value is worked out by hand in the test."""
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.evaluation.metrics import retrieval
from knowledge_assistant.application.evaluation.metrics.retrieval import (
    SOURCE,
    RankedChunk,
    evidence_hit_at_k,
    mean,
    overlaps,
    reciprocal_rank,
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
        evidence_hit_at_k([chunk("04", 0, 10, "x")], [], k=5)


# --- evidence hit -----------------------------------------------------------------------------------------------

QUOTE = "is activated per client request (connection), so scoped services can be injected"


def test_evidence_hit_false_when_the_quote_is_split_across_two_chunks():
    ranked = [chunk("11", 0, 30, "is activated per client request"),
              chunk("11", 30, 90, " (connection), so scoped services can be injected")]
    assert evidence_hit_at_k(ranked, [QUOTE], k=5) == 0
    assert evidence_hit_at_k([chunk("11", 0, 90, "x " + QUOTE + " y")], [QUOTE], k=5) == 1


def test_evidence_hit_ignores_whitespace_differences():
    text = "is  activated\nper client request (connection),\n\n  so scoped\tservices can be injected."
    assert QUOTE not in text
    assert evidence_hit_at_k([chunk("11", 0, 99, text)], [QUOTE], k=5) == 1


def test_evidence_hit_respects_k():
    ranked = [chunk("09", 0, 10, "noise")] * 5 + [chunk("11", 0, 99, QUOTE)]
    assert evidence_hit_at_k(ranked, [QUOTE], k=5) == 0
    assert evidence_hit_at_k(ranked, [QUOTE], k=6) == 1


def test_evidence_hit_any_quote_vs_all_quotes():
    quotes = [QUOTE, "The middleware is registered as a scoped or transient service"]
    ranked = [chunk("11", 0, 99, QUOTE)]
    assert evidence_hit_at_k(ranked, quotes, k=5) == 1
    assert evidence_hit_at_k(ranked, quotes, k=5, require_all=True) == 0
    ranked.append(chunk("11", 99, 200, quotes[1] + "."))
    assert evidence_hit_at_k(ranked, quotes, k=5, require_all=True) == 1


def test_evidence_hit_real_case_q_eval_028_no_break_space_in_source_18():
    """The #18 text has U+00A0 after 'C#'; the Arm A chunk holding the section must still count as a hit."""
    case = next(json.loads(line) for line in
                (ROOT / "data/evaluation/questions/eval-v1.jsonl").read_text(encoding="utf-8").splitlines()
                if '"Q-EVAL-028"' in line)
    quote = case["evidence"][0]["quote"]
    chunks = [RankedChunk.from_record(json.loads(line)) for line in
              (ROOT / "data/processed/chunks/arm-a.jsonl").read_text(encoding="utf-8").splitlines()
              if '"source_id": "18"' in line]
    holding = [c for c in chunks if "economical with regard to memory" in c.text]
    assert len(holding) == 1 and quote not in holding[0].text and " " in holding[0].text
    assert evidence_hit_at_k(holding, [quote], k=1) == 1


def test_whitespace_normalization_is_reused_from_validate_questions():
    filename = Path(retrieval.collapse_whitespace.__code__.co_filename).as_posix()
    assert filename.endswith("scripts/evaluation/validate_questions.py")
