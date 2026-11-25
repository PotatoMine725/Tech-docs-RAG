"""Benchmark v2: offline checks of the v2 question builder, validator rules and the corpus-2 section inventory.

Synthetic corpora only: corpus-2 converted text is git-ignored (ADR-0008), so the real-data validation runs through
scripts/evaluation/validate_questions_v2.py, not here.
"""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def _load(name, folder="evaluation"):
    path = ROOT / "scripts" / folder / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load("build_questions_v2")
validator = _load("validate_questions_v2")
converter = _load("convert_corpus2", "corpus2")

TEXT = "Intro line.\nHBsAg kéo dài trên 6 tháng là nhiễm mạn.\n| a | b |\n"
SIZES = {"C2-01": 2000}
C1 = ({"01"}, {("01", "Intro")}, {("01", "Intro"): [(1, "the cache is cleared at startup.")]})
C2 = ({"C2-01"}, {("C2-01", ""): [(1, validator.v1.collapse_whitespace(TEXT))]}, {"C2-01": TEXT})


def _draft(**changes):
    draft = {
        "id": "Q2-EVAL-001", "split": "eval", "category": "A_vi_on_vi", "corpus": "corpus2", "language": "vi",
        "question": "HBsAg kéo dài bao lâu thì là nhiễm mạn?", "answerable": True,
        "expected_answer": "Trên 6 tháng.",
        "answer_points": [{"id": "P1", "text": "Trên 6 tháng.", "required": True}],
        "expected_sources": [{"source_id": "C2-01", "heading_path": "", "slot": "S1"}],
        "evidence": [{"source_id": "C2-01", "heading_path": "", "supports": ["P1"],
                      "quote": "HBsAg kéo dài trên 6 tháng"}],
        "must_not_claim": ["3 months."], "cognitive_level": "recall", "difficulty": "easy",
    }
    draft.update(changes)
    return draft


def _case(**changes):
    return builder.expand(_draft(**changes), SIZES, {})


def _errors(case, split="eval"):
    errors = validator._schema_errors(case, split)
    return errors or validator.v1._ground_truth_errors(case) + validator._corpus_errors(case, C1, C2)


def test_a_valid_draft_expands_to_a_valid_draft_record():
    case = _case()
    assert _errors(case) == []
    assert case["status"] == "DRAFT" and case["typing"] == "diacritics" and case["size_class"] == "tiny"
    assert case["blueprint_id"] == "BP2-EVAL-001" and case["tags"]["failure_mode"] == "none"
    assert all(value is None for value in case["generated"].values())


def test_no_diacritics_typing_must_have_no_vietnamese_letters():
    plain = _case(typing="no_diacritics", question="HBsAg keo dai bao lau thi la nhiem man?")
    assert _errors(plain) == [] and plain["failure_mode"] == "no_diacritics"
    assert any("typing" in e for e in _errors(_case(typing="no_diacritics")))  # the question has diacritics
    assert any("typing" in e for e in _errors(_case(question="How long does HBsAg last?")))  # vi without marks


def test_quote_must_be_in_the_section_and_not_from_a_table_row():
    missing = copy.deepcopy(_draft())
    missing["evidence"][0]["quote"] = "HBsAg kéo dài trên 9 tháng"
    assert any("quote not found" in e for e in _errors(builder.expand(missing, SIZES, {})))
    table = copy.deepcopy(_draft())
    table["evidence"][0]["quote"] = "| a | b |"
    assert any("table row" in e for e in _errors(builder.expand(table, SIZES, {})))


def test_sources_must_be_accepted_documents_of_either_corpus():
    for bad in ("C2-02", "14", "25"):
        draft = _draft(size_class="medium")
        draft["expected_sources"] = [{"source_id": bad, "heading_path": "", "slot": "S1"}]
        assert any("not an accepted document" in e for e in _errors(builder.expand(draft, SIZES, {})))


def test_unanswerable_case_gets_refusal_and_absence_proof_terms_must_have_no_hits(tmp_path, monkeypatch):
    draft = _draft(category="F_unanswerable", answerable=False, answer_points=[], expected_sources=[], evidence=[])
    case = builder.expand(draft, {}, {"Q2-EVAL-001": "ABS2-001"})
    assert case["scope"] == "corpus-insufficient" and case["expected_behavior"] and _errors(case) == []
    proofs = tmp_path / "map.yaml"
    proofs.write_text("absence_proofs:\n  - {id: ABS2-001, zero_hit_terms: [dengue, nhiễm mạn]}\n", encoding="utf-8")
    monkeypatch.setattr(validator, "EVIDENCE_MAP", proofs)
    errors = validator._absence_errors([case], {"01": "no match here"}, {"C2-01": TEXT})
    assert errors == ["Q2-EVAL-001: absence term 'nhiễm mạn' found in ['#C2-01']"]


def test_frozen_validation_rejects_draft_cases(monkeypatch):
    monkeypatch.setattr(validator.v1, "load_corpus", lambda: C1)
    monkeypatch.setattr(validator, "load_corpus2", lambda: C2)
    monkeypatch.setattr(validator.v1, "read_jsonl", lambda path: [])
    monkeypatch.setattr(validator, "_absence_errors", lambda *args: [])
    cases = {"eval": [_case()], "dev": []}
    assert validator.validate(cases) == []
    assert validator.validate(cases, frozen=True) == ["Q2-EVAL-001: still DRAFT (freeze needs owner approval of every case)"]
    approved = builder.expand(_draft(review_status="approved"), SIZES, {})
    assert validator.validate({"eval": [approved], "dev": []}, frozen=True) == []


def test_heading_less_documents_get_one_whole_document_section():
    parsed = SimpleNamespace(sections=(), text="no headings at all\n")
    assert converter.sections("C2-01", parsed) == [
        {"source_id": "C2-01", "heading_path": "", "variant": 1, "char_start": 0, "char_end": 19}]
    span = SimpleNamespace(heading_path=("Title",), variant=1, char_start=5, char_end=19)
    parsed = SimpleNamespace(sections=(span,), text="pre\n\n# Title\nbody\n")
    assert [(s["heading_path"], s["char_start"], s["char_end"]) for s in converter.sections("C2-01", parsed)] == [
        ("", 0, 5), ("Title", 5, 19)]

