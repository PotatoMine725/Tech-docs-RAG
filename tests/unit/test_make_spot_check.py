"""EVAL-003c: `scripts/evaluation/make_spot_check.py`. Offline, made-up records (no eval-set content)."""
import io

from scripts.evaluation import make_spot_check
from tests.eval_report_fakes import judgement_line, span_dict, write_judgements, write_manifest, write_records, write_spans_file
from tests.judge_fakes import answer_verdict, make_record


def _row(result: str, language: str = "en", judge_status: str = "ok") -> tuple[dict, dict]:
    record = {"case_id": f"C-{result}-{language}-{id(result)}", "arm": "A", "language": language}
    return record, {"answer": {"result": result, "judge_status": judge_status}}


# --- judge_checked_pairs: only ok-judged records are eligible ------------------------------------------------

def test_judge_checked_pairs_excludes_records_without_an_ok_judge_verdict():
    ok_pair = _row("correct")
    missing_pair = ({"case_id": "c2", "arm": "A", "language": "en"}, {"answer": {"result": None, "judge_status": "missing"}})
    no_answer_pair = ({"case_id": "c3", "arm": "A", "language": "en"}, {"answer": None})
    eligible = make_spot_check.judge_checked_pairs([ok_pair, missing_pair, no_answer_pair])
    assert eligible == [ok_pair]


# --- stratified sampler: reproducible with a seed, covers every stratum with >= 1 record ---------------------

def _pairs(spec: list[tuple[str, str, int]]) -> list[tuple[dict, dict]]:
    """`spec`: [(result, language, count), ...] -> that many distinct records per (result, language) stratum."""
    pairs = []
    for result, language, count in spec:
        for n in range(count):
            record = {"case_id": f"Q-{result}-{language}-{n:02d}", "arm": "A", "language": language}
            pairs.append((record, {"answer": {"result": result, "judge_status": "ok"}}))
    return pairs


def test_sample_covers_every_non_empty_stratum_with_at_least_one_record():
    pairs = _pairs([("correct", "en", 5), ("correct", "vi", 1), ("incorrect", "en", 3), ("hallucination", "vi", 2)])
    sample = make_spot_check.sample_stratified(pairs, fraction=0.1, seed=1)  # a tiny fraction must still hit every stratum
    strata_present = {make_spot_check.stratum_key(record, row) for record, row in sample}
    assert strata_present == {("correct", "en"), ("correct", "vi"), ("incorrect", "en"), ("hallucination", "vi")}


def test_sample_is_reproducible_with_the_same_seed_and_changes_with_a_different_seed():
    pairs = _pairs([("correct", "en", 6), ("incorrect", "vi", 6)])
    first = make_spot_check.sample_stratified(pairs, fraction=0.5, seed=7)
    again = make_spot_check.sample_stratified(pairs, fraction=0.5, seed=7)
    assert [r["case_id"] for r, _ in first] == [r["case_id"] for r, _ in again]
    other_seed = make_spot_check.sample_stratified(pairs, fraction=0.5, seed=8)
    assert [r["case_id"] for r, _ in first] != [r["case_id"] for r, _ in other_seed]


def test_sample_size_is_never_larger_than_the_eligible_pool_and_never_exceeds_a_stratum():
    pairs = _pairs([("correct", "en", 2), ("incorrect", "vi", 2)])
    sample = make_spot_check.sample_stratified(pairs, fraction=1.0, seed=3)
    assert len(sample) == 4  # fraction 1.0: everything, no more, no duplicates
    assert len({record["case_id"] for record, _ in sample}) == 4


def test_sample_of_no_eligible_records_is_empty():
    assert make_spot_check.sample_stratified([], fraction=0.2, seed=42) == []


# --- rendering: fields are collapsed to one line so a case heading is never mistaken for the sheet's own markup

def test_a_multiline_cited_excerpt_is_collapsed_so_a_stray_heading_cannot_confuse_the_parser():
    record = make_record(1, cited=(1,))
    record["retrieved"][0]["display_text"] = "## Static classes\nA static class cannot be instantiated."
    rendered = make_spot_check.render_case(record, {"answer": {"result": "correct"}}, {}, None)
    assert "\n## Static classes" not in rendered  # never at the start of a rendered line
    assert "## Static classes A static class cannot be instantiated." in rendered


# --- end to end: builds a real sheet from a fake run, deterministically -------------------------------------

def build_fixture(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))
    r2 = make_record(2, answerable=True, cited=(1,))
    r2["language"] = "vi"
    write_records(directory, [r1, r2])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict()),
                                 judgement_line(r2, "answer", answer_verdict())])
    write_spans_file(tmp_path, {
        "Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}},
        "Q-TEST-002": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 2")]}},
    })
    return directory


def test_main_writes_a_sheet_with_every_judge_checked_case(tmp_path):
    build_fixture(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = make_spot_check.main(["--run", "run-1", "--fraction", "1.0", "--seed", "1"], root=tmp_path, out=out, err=err)
    assert code == make_spot_check.EXIT_OK, err.getvalue()
    sheet_path = tmp_path / "docs" / "reviews" / "evaluation" / "judge-spot-check-run-1.md"
    text = sheet_path.read_text(encoding="utf-8")
    assert "Q-TEST-001" in text and "Q-TEST-002" in text
    assert text.count("- **human_result:** ") == 2
    assert "<!-- run_id: run-1 -->" in text


def test_running_main_twice_is_byte_identical(tmp_path):
    build_fixture(tmp_path)
    sheet_path = tmp_path / "docs" / "reviews" / "evaluation" / "judge-spot-check-run-1.md"
    make_spot_check.main(["--run", "run-1"], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    first = sheet_path.read_bytes()
    make_spot_check.main(["--run", "run-1"], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert sheet_path.read_bytes() == first
