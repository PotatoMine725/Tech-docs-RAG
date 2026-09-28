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


# --- rendering: blind (no case id, arm or judge label), full ground truth, corpus text always blockquoted ------

def test_quote_block_prefixes_every_line_so_a_stray_heading_can_never_be_mistaken_for_a_case_heading():
    """Corpus text lives inside a `> ` blockquote; `## Static classes` at column 0 inside it would otherwise be
    indistinguishable from a real `## Sxx` case heading when the sheet is split on `^## `."""
    quoted = make_spot_check.quote_block("## Static classes\nA static class cannot be instantiated.")
    assert quoted == "> ## Static classes\n> A static class cannot be instantiated."
    assert "\n## Static classes" not in ("\n" + quoted)


def test_render_case_is_blind_no_case_id_arm_or_judge_label():
    record = make_record(1, answerable=True, cited=(1,))
    judgement = {"check": "answer", "verdict": {"required_points": [{"id": "P1", "covered": "yes"}]}}
    rendered = make_spot_check.render_case("S01", record, judgement)
    assert rendered.startswith("## S01 (answer check)")
    assert "Q-TEST-001" not in rendered  # case id
    assert "arm A" not in rendered and "arm" not in rendered.lower()
    assert "partially_correct" not in rendered and "correct" not in rendered.lower()  # no judge label leaks in


def test_render_case_answer_check_lists_only_required_points_and_every_cited_marker():
    points = [{"id": "P1", "text": "Required thing.", "required": True},
             {"id": "P2", "text": "Context only.", "required": False}]
    record = make_record(1, answerable=True, cited=(1, 2), points=points)
    judgement = {"check": "answer",
                "verdict": {"required_points": [{"id": "P1", "covered": "yes"}]}}
    rendered = make_spot_check.render_case("S01", record, judgement)
    assert "| P1 covered |  |  |" in rendered
    assert "| P2 covered |  |  |" not in rendered  # P2 is optional (context only), never a grading row
    assert "- P1 (required): Required thing." in rendered  # ground truth text, from the record itself
    assert "- P2 (optional, context only): Context only." in rendered
    assert "| citation [1] supports its claim |  |  |" in rendered
    assert "| citation [2] supports its claim |  |  |" in rendered
    assert "| agree with the judge? (fill after opening the key) |  |  |" in rendered


def test_render_case_refusal_check_has_only_the_presents_related_item():
    record = make_record(1, answerable=False, insufficient=True, cited=())
    judgement = {"check": "refusal", "verdict": {"presents_related_as_answer": False}}
    rendered = make_spot_check.render_case("S02", record, judgement)
    assert rendered.startswith("## S02 (refusal check)")
    assert "| presents_related_as_answer |  |  |" in rendered
    assert "P1 covered" not in rendered


def test_render_key_entry_carries_case_id_arm_run_and_label():
    record = make_record(1, answerable=True, cited=(1,))
    judgement = {"check": "answer", "judge_model": "test-judge-model", "verdict": {"reason": "Fine."}}
    entry = make_spot_check.render_key_entry("S01", "run-1", record, judgement, "correct")
    assert "## S01" in entry
    assert "- Case: `Q-TEST-001`, arm A, run `run-1`" in entry
    assert "label: **correct**" in entry
    assert '"reason": "Fine."' in entry


# --- end to end: builds real sheet + key from a fake run, deterministically ------------------------------------

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


def test_main_writes_a_blind_sheet_and_a_separate_key_with_every_judge_checked_case(tmp_path):
    build_fixture(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = make_spot_check.main(["--run", "run-1", "--fraction", "1.0", "--seed", "1"], root=tmp_path, out=out, err=err)
    assert code == make_spot_check.EXIT_OK, err.getvalue()
    sheet_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1.md"
    key_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1-judge.md"
    sheet, key = sheet_path.read_text(encoding="utf-8"), key_path.read_text(encoding="utf-8")
    assert "## S01" in sheet and "## S02" in sheet
    assert sheet.count("Q-TEST-001") == 0 and sheet.count("Q-TEST-002") == 0  # blind: no case id
    assert "Q-TEST-001" in key and "Q-TEST-002" in key  # the key carries the mapping
    assert "<!-- run_id: run-1 -->" in sheet


def test_running_main_twice_is_byte_identical(tmp_path):
    build_fixture(tmp_path)
    sheet_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1.md"
    key_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1-judge.md"
    make_spot_check.main(["--run", "run-1"], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    first_sheet, first_key = sheet_path.read_bytes(), key_path.read_bytes()
    make_spot_check.main(["--run", "run-1", "--force"], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert sheet_path.read_bytes() == first_sheet
    assert key_path.read_bytes() == first_key


def test_main_refuses_to_overwrite_an_existing_sheet_without_force(tmp_path):
    build_fixture(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = make_spot_check.main(["--run", "run-1"], root=tmp_path, out=out, err=err)
    assert code == make_spot_check.EXIT_OK, err.getvalue()
    sheet_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1.md"
    sheet_path.write_text("HAND-GRADED WORK\n", encoding="utf-8")
    code = make_spot_check.main(["--run", "run-1"], root=tmp_path, out=io.StringIO(), err=(err2 := io.StringIO()))
    assert code == make_spot_check.EXIT_ABORTED
    assert "--force" in err2.getvalue()
    assert sheet_path.read_text(encoding="utf-8") == "HAND-GRADED WORK\n"  # untouched


def test_main_with_force_overwrites_an_existing_sheet(tmp_path):
    build_fixture(tmp_path)
    sheet_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1.md"
    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_path.write_text("stale\n", encoding="utf-8")
    code = make_spot_check.main(["--run", "run-1", "--force"], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert code == make_spot_check.EXIT_OK
    assert "stale" not in sheet_path.read_text(encoding="utf-8")
