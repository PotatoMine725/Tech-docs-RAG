"""EVAL-003b-pre: expected section spans (`expected-spans-v1.json`) against the frozen eval set and the corpus."""
import json
from pathlib import Path

import pytest

from knowledge_assistant.application.evaluation.build_expected_spans import OUTPUT_FILE, expected_spans_document
from knowledge_assistant.application.evaluation.metrics.spans import (
    ALTERNATE,
    EXPECTED,
    build_expected_spans,
    spans_from_entry,
)

ROOT = Path(__file__).resolve().parents[3]
EVAL_FILE = ROOT / "data" / "evaluation" / "questions" / "eval-v1.jsonl"
FROZEN_EVAL_SHA256 = "3436870ef02dfc2c25bd9d403ec6c8dd44cb46dfacbf02d586161dedd1252937"  # eval-v1.md snapshot


def _committed() -> dict:
    return json.loads((ROOT / OUTPUT_FILE).read_text(encoding="utf-8"))


def _cases() -> list[dict]:
    return [json.loads(line) for line in EVAL_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_committed_file_matches_a_rebuild_from_the_current_inputs():
    assert _committed() == expected_spans_document(ROOT)


def test_built_from_the_frozen_eval_set():
    assert _committed()["inputs"]["questions"]["sha256"] == FROZEN_EVAL_SHA256


def test_every_answerable_case_has_a_non_empty_span_in_every_slot():
    entries = _committed()["cases"]
    cases = _cases()
    assert set(entries) == {case["id"] for case in cases}
    for case in cases:
        entry = entries[case["id"]]
        assert entry["answerable"] is case["answerable"]
        if not case["answerable"]:
            assert entry["slots"] == {}, case["id"]
            continue
        slots = {source["slot"] for source in case["expected_sources"]}
        assert set(entry["slots"]) == slots, case["id"]
        for slot, spans in entry["slots"].items():
            assert any(span["char_end"] > span["char_start"] for span in spans), (case["id"], slot)
            # strict hit needs an expected span in every slot
            assert any(span["role"] == EXPECTED for span in spans), (case["id"], slot)


def test_every_listed_source_is_tagged_with_its_role():
    entries = _committed()["cases"]
    for case in _cases():
        spans = spans_from_entry(entries[case["id"]])
        for role, refs in ((EXPECTED, case["expected_sources"]), (ALTERNATE, case["acceptable_alternate_sources"])):
            for ref in refs:
                assert any((s.slot, s.role, s.source_id, s.heading_path)
                           == (ref["slot"], role, ref["source_id"], ref["heading_path"]) for s in spans), ref


def _record(source_id, sections):
    return {"id": source_id, "metadata": {"sections": [
        {"heading_path": path, "variant": variant, "char_start": start, "char_end": end}
        for path, variant, start, end in sections]}}


def _case(expected, alternates=(), answerable=True):
    return {"id": "Q-T", "answerable": answerable,
            "expected_sources": [{"source_id": s, "heading_path": h, "slot": slot} for s, h, slot in expected],
            "acceptable_alternate_sources": [{"source_id": s, "heading_path": h, "slot": slot}
                                             for s, h, slot in alternates]}


def test_every_variant_of_a_heading_path_becomes_a_span():
    records = [_record("13", [("A", 1, 0, 50), ("A > B", 1, 50, 80), ("A", 2, 80, 120), ("A > B", 2, 120, 150)])]
    entry = build_expected_spans(records, [_case([("13", "A > B", "S1")], [("13", "A", "S1")])])["Q-T"]
    assert [(s["role"], s["variant"], s["char_start"], s["char_end"]) for s in entry["slots"]["S1"]] == [
        (EXPECTED, 1, 50, 80), (EXPECTED, 2, 120, 150), (ALTERNATE, 1, 0, 50), (ALTERNATE, 2, 80, 120)]


def test_slots_are_ordered_numerically():
    records = [_record("04", [("X", 1, 0, 10)])]
    case = _case([("04", "X", f"S{n}") for n in (10, 2, 1)])
    assert list(build_expected_spans(records, [case])["Q-T"]["slots"]) == ["S1", "S2", "S10"]


def test_unknown_section_raises_instead_of_producing_an_unhittable_slot():
    with pytest.raises(ValueError, match="not in the normalized corpus"):
        build_expected_spans([_record("04", [("X", 1, 0, 10)])], [_case([("04", "Y", "S1")])])


def test_corpus_insufficient_case_has_no_slots():
    assert build_expected_spans([], [_case([], answerable=False)])["Q-T"] == {"answerable": False, "slots": {}}
