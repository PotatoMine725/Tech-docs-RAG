"""EVAL-003b: the duplicate overlap rule (owner decision, EVAL-003b addendum 2026-09-27; RAG-002 ledger note; scope
narrowed by the owner the same day: section level only).

For span (section-level) metrics, lenient and strict, a retrieved chunk counts as overlapping a span if it OR any chunk
in its `duplicate_chunk_ids` does. Source metrics use the kept chunk's own document (what the user sees). The retriever keeps one chunk per `passage_hash` group (RAG-002) and lists the dropped
copies; the copy it kept can sit in another document (the doc 12/13 pair) than the one the ground truth names.
Offsets and documents are made up; every expected value is worked out by hand.
"""
import pytest

from knowledge_assistant.application.evaluation.metrics.retrieval import (
    SOURCE,
    RankedChunk,
    duplicate_rule_changes,
    evidence_hit_via_alternate_only_at_k,
    reciprocal_rank,
    section_hit_at_k,
    slot_fraction_at_k,
    source_hit_at_k,
)
from knowledge_assistant.application.evaluation.metrics.spans import ALTERNATE, EXPECTED, ExpectedSpan


def span(source_id, start, end, slot="S1", role=EXPECTED):
    return ExpectedSpan(slot, role, source_id, f"#{source_id} section", 1, start, end)


# The kept chunk is #13 [500, 600); its dropped copy is #12 [100, 200). The expected section is #12 [150, 400).
KEPT_IN_13 = RankedChunk("13", 500, 600, "same passage", duplicates=(("12", 100, 200),))
SPANS_12 = [span("12", 150, 400)]


def test_a_duplicate_that_overlaps_the_span_makes_the_kept_chunk_a_section_hit():
    assert section_hit_at_k([KEPT_IN_13], SPANS_12, k=5) == 1
    assert section_hit_at_k([KEPT_IN_13], SPANS_12, k=5, strict=True) == 1


def test_source_metrics_use_the_kept_chunks_own_document():
    """Owner, 2026-09-27: the kept #13 chunk is a #13 source, whatever its dropped #12 copy is."""
    assert source_hit_at_k([KEPT_IN_13], SPANS_12, k=5) == 0
    assert source_hit_at_k([KEPT_IN_13], SPANS_12, k=5, strict=True) == 0
    assert reciprocal_rank([KEPT_IN_13], SPANS_12, level=SOURCE) == 0.0
    assert slot_fraction_at_k([KEPT_IN_13], SPANS_12, k=5, level=SOURCE) == 0.0


def test_without_the_duplicate_the_same_chunk_misses():
    alone = RankedChunk("13", 500, 600, "same passage")
    assert section_hit_at_k([alone], SPANS_12, k=5) == 0
    assert source_hit_at_k([alone], SPANS_12, k=5) == 0


def test_a_touching_duplicate_does_not_overlap():
    touching = RankedChunk("13", 500, 600, duplicates=(("12", 50, 150),))  # ends where the span starts
    assert section_hit_at_k([touching], SPANS_12, k=5) == 0


def test_duplicate_rule_is_strict_aware():
    spans = [span("12", 150, 400, role=EXPECTED), span("13", 0, 50, role=ALTERNATE)]
    kept = RankedChunk("12", 900, 950, duplicates=(("13", 10, 40),))  # the copy overlaps the alternate only
    assert section_hit_at_k([kept], spans, k=5) == 1
    assert section_hit_at_k([kept], spans, k=5, strict=True) == 0


def test_duplicate_rule_in_mrr_and_slot_fraction():
    spans = [span("12", 150, 400, slot="S1"), span("20", 0, 100, slot="S2")]
    miss = RankedChunk("05", 0, 100)
    assert reciprocal_rank([miss, KEPT_IN_13], spans) == pytest.approx(0.5)
    assert reciprocal_rank([miss, KEPT_IN_13], spans, level=SOURCE) == 0.0  # source level: the kept chunk's own #13
    assert slot_fraction_at_k([miss, KEPT_IN_13], spans, k=5) == pytest.approx(0.5)


def test_duplicate_counts_as_inside_the_expected_spans_for_the_alternate_only_diagnostic():
    spans = [span("12", 150, 400), span("30", 0, 1000, role=ALTERNATE)]
    kept = RankedChunk("13", 500, 600, "the quote is here", duplicates=(("12", 100, 200),))
    assert evidence_hit_via_alternate_only_at_k([kept], {"P1": ["the quote is here"]}, spans, k=5) == 0


def test_from_record_resolves_duplicate_ids_through_the_chunk_index():
    entry = {"source_id": "13", "char_start": 500, "char_end": 600, "display_text": "same passage",
             "duplicate_chunk_ids": ["12:header-1600:0003"]}
    index = {"12:header-1600:0003": ("12", 100, 200)}
    assert RankedChunk.from_record(entry, index) == KEPT_IN_13


def test_from_record_refuses_duplicates_without_a_chunk_index():
    entry = {"source_id": "13", "char_start": 500, "char_end": 600, "display_text": "x",
             "duplicate_chunk_ids": ["12:header-1600:0003"]}
    with pytest.raises(ValueError, match="duplicate"):
        RankedChunk.from_record(entry)


def test_from_record_refuses_an_unknown_duplicate_id():
    entry = {"source_id": "13", "char_start": 500, "char_end": 600, "display_text": "x",
             "duplicate_chunk_ids": ["12:header-1600:0099"]}
    with pytest.raises(ValueError, match="12:header-1600:0099"):
        RankedChunk.from_record(entry, {})


def test_from_record_without_duplicates_needs_no_index():
    entry = {"source_id": "13", "char_start": 500, "char_end": 600, "display_text": "x", "duplicate_chunk_ids": []}
    assert RankedChunk.from_record(entry) == RankedChunk("13", 500, 600, "x")


def test_duplicate_rule_changes_names_every_value_the_rule_changed():
    changed = duplicate_rule_changes([KEPT_IN_13], SPANS_12)
    # section level only: k = 1, 3, 5 x lenient/strict hit, lenient and strict MRR, the section slot fraction
    assert "section_hit@5" in changed and "section_hit@1:strict" in changed and "mrr:strict" in changed
    assert not [name for name in changed if name.startswith("source")]
    assert len(changed) == 6 + 2 + 1


def test_duplicate_rule_changes_is_empty_without_duplicates_or_when_the_kept_chunk_already_hits():
    assert duplicate_rule_changes([RankedChunk("13", 500, 600)], SPANS_12) == []
    already = RankedChunk("12", 160, 180, duplicates=(("13", 0, 10),))
    assert duplicate_rule_changes([already], SPANS_12) == []
