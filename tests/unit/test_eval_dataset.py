"""EVAL-002: offline checks for the question files (eval-v1.jsonl, dev-v1.jsonl) and their validator."""
import copy
import importlib.util
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "evaluation"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load("validate_questions")
builder = _load("build_question_files")


@pytest.fixture(scope="module")
def corpus():
    return validator.load_corpus()


@pytest.fixture(scope="module")
def files():
    return validator.read_jsonl(validator.EVAL_FILE), validator.read_jsonl(validator.DEV_FILE)


def _by_id(cases, case_id):
    return next(c for c in cases if c["id"] == case_id)


def test_question_files_pass_the_validator(files, corpus):
    eval_cases, dev_cases = files
    assert validator.validate(eval_cases, dev_cases, corpus) == []


def test_question_files_are_exactly_the_build_output():
    """Ground truth is copied from blueprint.yaml, never edited by hand; files are LF, UTF-8."""
    for split, cases in builder.build().items():
        assert builder.OUTPUTS[split].read_bytes() == builder.render(cases).encode("utf-8"), split


def test_eval_set_keeps_the_od4_mix(files):
    eval_cases, dev_cases = files
    assert len(eval_cases) == 36 and len(dev_cases) == 6
    assert Counter(c["scope"] for c in eval_cases) == {"single-source": 28, "cross-document": 4, "corpus-insufficient": 4}
    assert Counter(c["language"] for c in eval_cases) == {"en": 18, "vi": 18}
    assert len({c["parallel_group_id"] for c in eval_cases if c["parallel_group_id"]}) == 7


def test_generated_fields_are_null_and_separate(files):
    for case in files[0] + files[1]:
        assert case["generated"] == {"generated_answer": None, "citations": None, "result": None}, case["id"]


def test_evidence_slots_are_kept_not_flattened(files):
    """Owner decision D1: sources keep their slot; the two-slot single-source cases keep both slots."""
    eval_cases = files[0]
    for case_id in ("Q-EVAL-017", "Q-EVAL-022", "Q-EVAL-029", "Q-EVAL-030", "Q-EVAL-031", "Q-EVAL-032"):
        assert {s["slot"] for s in _by_id(eval_cases, case_id)["expected_sources"]} == {"S1", "S2"}, case_id
    alternates = _by_id(eval_cases, "Q-EVAL-031")["acceptable_alternate_sources"]
    assert [(a["source_id"], a["slot"]) for a in alternates if a["source_id"] == "20"] == [("20", "S2")]


# --- the validator must catch each kind of bad ground truth (mutation checks) ---

def _mutated(files, case_id, change):
    eval_cases, dev_cases = copy.deepcopy(files)
    change(_by_id(eval_cases, case_id))
    return eval_cases, dev_cases


@pytest.mark.parametrize("case_id, change, expected", [
    ("Q-EVAL-001", lambda c: c["evidence"][0].update(quote="Queries are never executed against the database."), "quote not found"),
    ("Q-EVAL-021", lambda c: c["evidence"][0].update(heading_path="A tour of the C# language"), "quote not found"),
    ("Q-EVAL-001", lambda c: c["expected_sources"][0].update(heading_path="Querying Data > Invented"), "not in the section inventory"),
    ("Q-EVAL-001", lambda c: c["expected_sources"][0].update(source_id="14"), "not an accepted document"),
    ("Q-EVAL-033", lambda c: c["near_miss_sources"].append("25"), "not an accepted document"),
    ("Q-EVAL-002", lambda c: c["answer_points"][0].update(text="Changed."), "answer_points differs"),
    ("Q-EVAL-004", lambda c: c["expected_sources"][0].update(slot="S2"), "expected_sources differs"),
    ("Q-EVAL-015", lambda c: c.update(evidence=[]), "required points without evidence"),
    ("Q-EVAL-017", lambda c: c["acceptable_alternate_sources"][0].update(slot="S9"), "alternate source in a slot"),
    ("Q-EVAL-005", lambda c: c["generated"].update(generated_answer="text"), "generated fields must be null"),
    ("Q-EVAL-005", lambda c: c.update(difficulty="hard"), "tags differ"),
    ("Q-EVAL-006", lambda c: c.update(question="Why is this wrong?", question_chars=18), "does not look like language"),
    ("Q-EVAL-034", lambda c: c["expected_sources"].append({"source_id": "23", "heading_path": "Routing in ASP.NET Core", "slot": "S1"}), "unanswerable case must have no sources"),
])
def test_validator_rejects_bad_cases(files, corpus, case_id, change, expected):
    errors = validator.validate(*_mutated(files, case_id, change), corpus)
    assert any(expected in e for e in errors), errors


def test_validator_rejects_overlap_and_too_few_cases(files, corpus):
    eval_cases, dev_cases = copy.deepcopy(files)
    dev_cases.append(copy.deepcopy(eval_cases[0]) | {"split": "dev", "id": "Q-DEV-099"})
    errors = validator.validate(eval_cases, dev_cases, corpus)
    assert any("eval and dev share" in e for e in errors), errors
    errors = validator.validate(files[0][:29], files[1], corpus)
    assert any("at least 30 required" in e for e in errors), errors
    errors = validator.validate(files[0] + [copy.deepcopy(files[0][0])], files[1], corpus)
    assert any("duplicate ID Q-EVAL-001" in e for e in errors), errors


def test_validator_rejects_shared_expected_section_alone(files, corpus):
    """Only the expected section is shared (ID, blueprint and question all differ), so only that check can fire."""
    eval_cases, dev_cases = copy.deepcopy(files)
    dev_cases[0]["expected_sources"] = copy.deepcopy(eval_cases[0]["expected_sources"])
    errors = validator.validate(eval_cases, dev_cases, corpus)
    assert any("eval and dev share expected sections" in e for e in errors), errors
    assert not any(f"share {field}" in e for e in errors for field in ("id", "blueprint_id", "question")), errors
