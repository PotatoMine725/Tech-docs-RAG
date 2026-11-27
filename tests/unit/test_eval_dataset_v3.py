"""dev-v3: offline checks of the v3 question builder and validator rules on synthetic data.

Corpus-2 converted text is git-ignored (ADR-0008), so the real-data validation runs through
scripts/evaluation/validate_questions_v3.py, not here.
"""
import importlib.util
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    path = ROOT / "scripts" / "evaluation" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = _load("build_questions_v3")
validator = _load("validate_questions_v3")

TEXT = "Intro.\nHBsAg kéo dài trên 6 tháng là nhiễm mạn.\n"
C1 = ({"01"}, {("01", "Intro")}, {("01", "Intro"): [(1, "the cache is cleared at startup.")]})
C2 = ({"C2-01"}, {("C2-01", ""): [(1, unicodedata.normalize("NFD", TEXT))]}, {"C2-01": TEXT})


def _draft(**changes):
    draft = {
        "id": "Q3-DEV-001", "review_status": "draft", "split": "dev", "category": "A_vi_on_vi", "corpus": "corpus2",
        "language": "vi", "question_language": "vi", "question": "HBsAg kéo dài bao lâu thì là nhiễm mạn?",
        "answerable": True, "expected_answer": "Trên 6 tháng.",
        "answer_points": [{"id": "P1", "text": "Trên 6 tháng.", "required": True}],
        "expected_sources": [{"source_id": "C2-01", "heading_path": "", "slot": "S1"}],
        "evidence": [{"source_id": "C2-01", "heading_path": "", "supports": ["P1"], "quote": "HBsAg kéo dài trên 6 tháng"}],
        "must_not_claim": ["3 months."], "cognitive_level": "recall", "difficulty": "easy",
    }
    draft.update(changes)
    return draft


def _case(**changes):
    return builder.expand(_draft(**changes), {"C2-01": 2000}, {})


def test_expand_sets_the_v3_fields_and_passes_the_v3_schema():
    case = _case()
    assert case["blueprint_id"] == "BP3-DEV-001" and case["status"] == "DRAFT" and case["question_language"] == "vi"
    assert validator.schema_errors(case) == []
    assert validator.corpus_errors(case, C1, C2) == []


def test_mixed_question_must_be_answered_in_vietnamese():
    assert validator.schema_errors(_case(question_language="mixed")) == []
    assert any("question_language" in e for e in validator.schema_errors(_case(question_language="en")))


def test_v2_ids_are_rejected_by_the_v3_pattern():
    assert any("ID does not match" in e for e in validator.schema_errors(_case(id="Q2-DEV-001")))


def test_quote_check_is_nfc_insensitive_and_catches_invented_quotes():
    nfd_quote = unicodedata.normalize("NFD", "kéo dài trên 6 tháng")
    assert validator.quote_in(nfd_quote, [TEXT]) and validator.quote_in("kéo dài trên 6 tháng", [C2[1][("C2-01", "")][0][1]])
    bad = _case(evidence=[{**_draft()["evidence"][0], "quote": "kéo dài trên 3 tháng"}])
    assert any("quote not found" in e for e in validator.corpus_errors(bad, C1, C2))


def test_zero_hit_search_matches_with_and_without_diacritics():
    corpus = {"#C2-01": (TEXT.lower(), validator.fold(TEXT))}
    assert validator.term_hits("keo dai", corpus) == ["#C2-01"]
    assert validator.term_hits("KÉO DÀI", corpus) == ["#C2-01"]
    assert validator.term_hits("viêm gan C", corpus) == []
    assert validator.fold("Đông đặc") == "dong dac"


def test_absence_proof_must_belong_to_its_question():
    case = _case(answerable=False, expected_answer=None, answer_points=[], expected_sources=[], evidence=[])
    case = {**case, "absence_proof": "ABS3-001"}
    corpus = {"#C2-01": (TEXT.lower(), validator.fold(TEXT))}
    good = {"ABS3-001": {"id": "ABS3-001", "question": "Q3-DEV-001", "zero_hit_terms": ["dengue"]}}
    assert validator.absence_errors([case], good, corpus) == []
    hit = {"ABS3-001": {**good["ABS3-001"], "zero_hit_terms": ["nhiem man"]}}
    assert any("found in" in e for e in validator.absence_errors([case], hit, corpus))
    other = {"ABS3-001": {**good["ABS3-001"], "question": "Q3-DEV-002"}}
    assert validator.absence_errors([case], other, corpus)


def test_eval_section_overlap_and_paraphrase_measure():
    case = _case()
    eval_case = {"expected_sources": [{"source_id": "C2-01", "heading_path": ""}], "acceptable_alternate_sources": []}
    assert validator.overlap_errors([case], [eval_case])
    assert validator.overlap_errors([case], [{**eval_case, "expected_sources": [{"source_id": "C2-01", "heading_path": "x"}]}]) == []
    assert validator.jaccard("Hội chứng đông đặc phổi", "hoi chung dong dac phoi") == 1.0


def test_builder_numbers_absence_proofs_in_id_order():
    unanswerable = dict(answerable=False, expected_sources=[], evidence=[], answer_points=[],
                        absence={"topic": "t", "zero_hit_terms": ["x"]})
    drafts = [_draft(id="Q3-DEV-002", **unanswerable), _draft()]
    records, proofs = builder.build(sorted(drafts, key=lambda d: d["id"]), {"C2-01": 2000})
    assert [p["id"] for p in proofs] == ["ABS3-001"] and proofs[0]["question"] == "Q3-DEV-002"
    assert records[1]["absence_proof"] == "ABS3-001" and records[1]["scope"] == "corpus-insufficient"
