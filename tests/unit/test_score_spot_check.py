"""EVAL-003c: `scripts/evaluation/score_spot_check.py`. Offline, made-up data (no eval-set content) except the one
real-data test, which is read-only against the actual EVAL-004a owner-graded sheet (VERIFY EVAL-003c check 5)."""
import io
import json
from pathlib import Path

import pytest

from scripts.evaluation import make_spot_check, score_spot_check
from tests.eval_report_fakes import judgement_line, span_dict, write_judgements, write_manifest, write_records, write_spans_file
from tests.judge_fakes import answer_verdict, make_record, refusal_verdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# A fixture that copies the real sheet's structure: two cases, blind headings, an Owner verdict table each, and a
# separate key file - one point covered "no" by the owner where the judge said "yes" (a rule-based disagreement).
SHEET = """# Judge spot-check: owner grading sheet (blind)

Preamble text the parser must ignore.

## S01 (answer check)

**Question** (en):

> What does part 1 say?

**Ground truth**

- Expected answer: Part 1 says so.
- P1 (required): Part 1 says so.

**Answer**:

> Part 1 says so [1].

**Cited passages** (1):

[1] #01 — Doc > Part 1

> ## Static classes
> A static class cannot be instantiated.

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| P1 covered | {p1} |  |
| contradicts ground truth | no |  |
| unsupported claims | no |  |
| citation [1] supports its claim | yes |  |
| agree with the judge? (fill after opening the key) | {agree1} |  |

## S02 (refusal check)

**Question** (en):

> What does part 2 say?

**Ground truth**

- Expected answer: The documents do not cover this.

**Answer**:

> The document collection does not contain enough information to answer this question.

**Cited passages** (0):

**Owner verdict**

| Item | Owner | Note |
|---|---|---|
| presents_related_as_answer | {presents} |  |
| agree with the judge? (fill after opening the key) | {agree2} |  |
"""

KEY = """# Judge spot-check: the judge's verdicts (key)

## S01

- Case: `Q-TEST-001`, arm A, run `run-1`
- Check: answer; judge model `test-judge-model`; label: **correct**

```json
{
 "required_points": [{"id": "P1", "covered": "yes"}],
 "contradicts_ground_truth": false,
 "unsupported_claims": [],
 "citations": [{"marker": 1, "supports_attached_claim": "yes"}],
 "reason": "P1 is fully covered."
}
```

## S02

- Case: `Q-TEST-002`, arm A, run `run-1`
- Check: refusal; judge model `test-judge-model`; label: **correct_refusal**

```json
{
 "presents_related_as_answer": false,
 "reason": "Correctly refuses."
}
```
"""


def sheet(p1="yes", agree1="yes", presents="false", agree2="yes"):
    return SHEET.format(p1=p1, agree1=agree1, presents=presents, agree2=agree2)


def build_run(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))
    r2 = make_record(2, answerable=False, insufficient=True, cited=())
    write_records(directory, [r1, r2])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict()),
                                 judgement_line(r2, "refusal", refusal_verdict(False))])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})


# --- parsing the owner's blind sheet: never mistakes a blockquoted "##" for a case heading ---------------------

def test_parse_owner_sheet_finds_both_cases_and_their_check_type():
    cases = score_spot_check.parse_owner_sheet(sheet())
    assert set(cases) == {"S01", "S02"}
    assert cases["S01"]["check"] == "answer" and cases["S02"]["check"] == "refusal"
    assert "## Static classes" not in str(cases)  # the blockquoted corpus heading was never split on


def test_parse_owner_sheet_reads_the_owner_verdict_table_including_blank_notes():
    cases = score_spot_check.parse_owner_sheet(sheet())
    assert cases["S01"]["grades"]["P1 covered"] == ("yes", "")
    assert cases["S02"]["grades"]["presents_related_as_answer"] == ("false", "")


# --- refuses while any owner grade is blank ---------------------------------------------------------------------

def test_check_filled_raises_naming_every_blank_cell():
    cases = score_spot_check.parse_owner_sheet(sheet(p1=""))
    with pytest.raises(score_spot_check.SpotCheckError, match="S01:P1 covered"):
        score_spot_check.check_filled(cases)


def test_check_filled_passes_when_every_cell_is_filled():
    score_spot_check.check_filled(score_spot_check.parse_owner_sheet(sheet()))  # does not raise


# --- parsing the key file -----------------------------------------------------------------------------------

def test_parse_key_reads_case_arm_run_label_and_the_verdicts_reason():
    key = score_spot_check.parse_key(KEY)
    entry = key["S01"]
    assert {k: v for k, v in entry.items() if k != "verdict"} == \
        {"case_id": "Q-TEST-001", "arm": "A", "run_id": "run-1", "check": "answer",
         "label": "correct", "reason": "P1 is fully covered."}
    assert entry["verdict"]["required_points"] == [{"id": "P1", "covered": "yes"}]
    assert key["S02"]["label"] == "correct_refusal" and key["S02"]["reason"] == "Correctly refuses."


def test_point_level_diffs_finds_the_specific_disagreeing_point():
    grades = {"P1 covered": ("no", ""), "contradicts ground truth": ("no", ""), "unsupported claims": ("no", "")}
    verdict = {"required_points": [{"id": "P1", "covered": "yes"}], "contradicts_ground_truth": False}
    diffs = score_spot_check.point_level_diffs("answer", grades, verdict)
    assert diffs == ["P1: owner='no', judge='yes'"]


def test_point_level_diffs_empty_when_owner_and_judge_agree_on_every_point():
    grades = {"P1 covered": ("yes", ""), "contradicts ground truth": ("no", ""), "unsupported claims": ("no", "")}
    verdict = {"required_points": [{"id": "P1", "covered": "yes"}], "contradicts_ground_truth": False}
    assert score_spot_check.point_level_diffs("answer", grades, verdict) == []


# --- deriving the owner's rule-based label via metrics.mapping.map_result ----------------------------------------

def test_owner_label_answer_check_matches_the_judges_label_when_grades_agree():
    cases = score_spot_check.parse_owner_sheet(sheet(p1="yes"))
    record = make_record(1, answerable=True, cited=(1,))
    assert score_spot_check.owner_label("S01", "answer", cases["S01"]["grades"], record) == "correct"


def test_owner_label_answer_check_diverges_from_the_judge_when_the_owner_marks_a_point_no():
    """The judge said P1=yes (label correct); the owner marking it `no` must map to a different (rule-based) label -
    this is the disagreement the holistic self-reported column can miss."""
    cases = score_spot_check.parse_owner_sheet(sheet(p1="no"))
    record = make_record(1, answerable=True, cited=(1,))
    assert score_spot_check.owner_label("S01", "answer", cases["S01"]["grades"], record) == "incorrect"


def test_owner_label_refusal_check_reads_presents_related_as_answer():
    cases = score_spot_check.parse_owner_sheet(sheet(presents="false"))
    record = make_record(2, answerable=False, insufficient=True, cited=())
    assert score_spot_check.owner_label("S02", "refusal", cases["S02"]["grades"], record) == "correct_refusal"


def test_holistic_agreement_reads_the_self_reported_column_independently_of_map_result():
    cases = score_spot_check.parse_owner_sheet(sheet(p1="no", agree1="yes"))  # rule-based disagrees, holistic says yes
    assert score_spot_check.holistic_agreement(cases["S01"]["grades"]) is True


# --- agreement / kappa / confusion / disagreements (pure, same math as before) -----------------------------------

def test_agreement_rate_on_full_agreement():
    assert score_spot_check.agreement_rate([("correct", "correct"), ("incorrect", "incorrect")]) == \
        {"n": 2, "count": 2, "value": 1.0}


def test_cohens_kappa_hand_computed_two_by_two_example():
    pairs = [("A", "A"), ("A", "B"), ("B", "B"), ("B", "B")]
    assert score_spot_check.agreement_rate(pairs)["value"] == pytest.approx(0.75)
    assert score_spot_check.cohens_kappa(pairs) == pytest.approx(0.5)


def test_cohens_kappa_of_no_pairs_is_none():
    assert score_spot_check.cohens_kappa([]) is None


def test_confusion_matrix_counts_judge_rows_against_owner_columns():
    pairs = [("correct", "correct"), ("correct", "incorrect"), ("incorrect", "incorrect")]
    labels, matrix = score_spot_check.confusion_matrix(pairs)
    assert labels == ["correct", "incorrect"]
    assert matrix["correct"]["correct"] == 1 and matrix["correct"]["incorrect"] == 1
    assert matrix["incorrect"]["incorrect"] == 1 and matrix["incorrect"]["correct"] == 0


# --- joining sheet + key + records, and end to end --------------------------------------------------------------

def test_rule_based_pairs_raises_on_an_sid_mismatch_between_sheet_and_key():
    cases = score_spot_check.parse_owner_sheet(sheet())
    key = score_spot_check.parse_key(KEY)
    del key["S02"]
    with pytest.raises(score_spot_check.SpotCheckError, match="S02"):
        score_spot_check.rule_based_pairs(cases, key, {"S01": {}})


def test_main_refuses_on_a_blank_sheet_and_writes_nothing(tmp_path):
    build_run(tmp_path)
    sheet_path, key_path = tmp_path / "sheet.md", tmp_path / "key.md"
    sheet_path.write_text(sheet(p1=""), encoding="utf-8")
    key_path.write_text(KEY, encoding="utf-8")
    report_path = tmp_path / "report.md"
    report_path.write_text("# Report\nkeep me\n", encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    code = score_spot_check.main([str(sheet_path), str(key_path), "--out", str(report_path)],
                                 root=tmp_path, out=out, err=err)
    assert code == score_spot_check.EXIT_ABORTED
    assert report_path.read_text(encoding="utf-8") == "# Report\nkeep me\n"  # untouched


def test_main_scores_a_filled_sheet_and_fills_the_marker_without_touching_the_rest(tmp_path):
    build_run(tmp_path)
    sheet_path, key_path = tmp_path / "sheet.md", tmp_path / "key.md"
    sheet_path.write_text(sheet(p1="no"), encoding="utf-8")  # disagrees with the judge (rule-based)
    key_path.write_text(KEY, encoding="utf-8")
    report_path = tmp_path / "report.md"
    report_path.write_text(
        "# Report\n\nBefore.\n\n<!-- AUTO:judge_agreement -->\nplaceholder\n<!-- /AUTO:judge_agreement -->\n\nAfter.\n",
        encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    code = score_spot_check.main([str(sheet_path), str(key_path), "--out", str(report_path)],
                                 root=tmp_path, out=out, err=err)
    assert code == score_spot_check.EXIT_OK, err.getvalue()
    text = report_path.read_text(encoding="utf-8")
    assert "Before." in text and "After." in text and "placeholder" not in text
    assert "0.500" in text  # 1/2 rule-based agreement (S01 disagrees, S02 agrees)
    assert "S01" in text  # listed as a disagreement


def test_main_never_edits_the_sheet_or_the_key(tmp_path):
    build_run(tmp_path)
    sheet_path, key_path = tmp_path / "sheet.md", tmp_path / "key.md"
    sheet_path.write_text(sheet(), encoding="utf-8")
    key_path.write_text(KEY, encoding="utf-8")
    before_sheet, before_key = sheet_path.read_bytes(), key_path.read_bytes()
    score_spot_check.main([str(sheet_path), str(key_path), "--out", str(tmp_path / "report.md")],
                          root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert sheet_path.read_bytes() == before_sheet
    assert key_path.read_bytes() == before_key


def test_running_score_spot_check_twice_on_the_same_inputs_is_byte_identical(tmp_path):
    build_run(tmp_path)
    sheet_path, key_path = tmp_path / "sheet.md", tmp_path / "key.md"
    sheet_path.write_text(sheet(), encoding="utf-8")
    key_path.write_text(KEY, encoding="utf-8")
    report_path = tmp_path / "report.md"
    score_spot_check.main([str(sheet_path), str(key_path), "--out", str(report_path)],
                          root=tmp_path, out=io.StringIO(), err=io.StringIO())
    first = report_path.read_bytes()
    score_spot_check.main([str(sheet_path), str(key_path), "--out", str(report_path)],
                          root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert report_path.read_bytes() == first


# --- round trip: make_spot_check.py's own output is exactly what score_spot_check.py reads -----------------------

def test_a_sheet_and_key_written_by_make_spot_check_can_be_filled_and_scored(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))
    write_records(directory, [r1])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict())])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})
    code = make_spot_check.main(["--run", "run-1", "--fraction", "1.0"], root=tmp_path,
                                out=io.StringIO(), err=io.StringIO())
    assert code == make_spot_check.EXIT_OK
    sheet_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1.md"
    key_path = tmp_path / "validation" / "evaluation" / "judge-spot-check-run-1-judge.md"
    filled = sheet_path.read_text(encoding="utf-8").replace(
        "| P1 covered |  |  |", "| P1 covered | yes |  |").replace(
        "| contradicts ground truth |  |  |", "| contradicts ground truth | no |  |").replace(
        "| unsupported claims |  |  |", "| unsupported claims | no |  |").replace(
        "| citation [1] supports its claim |  |  |", "| citation [1] supports its claim | yes |  |").replace(
        "| agree with the judge? (fill after opening the key) |  |  |",
        "| agree with the judge? (fill after opening the key) | yes |  |")
    sheet_path.write_text(filled, encoding="utf-8")
    report_path = tmp_path / "report.md"
    out, err = io.StringIO(), io.StringIO()
    code = score_spot_check.main([str(sheet_path), str(key_path), "--out", str(report_path)],
                                 root=tmp_path, out=out, err=err)
    assert code == score_spot_check.EXIT_OK, err.getvalue()
    assert "1.000 (1/1)" in report_path.read_text(encoding="utf-8")


# --- real data (read-only): the actual EVAL-004a owner-graded sheet (VERIFY EVAL-003c check 5) -------------------

def test_score_spot_check_on_the_real_eval_004a_sheet_matches_the_owners_corrected_figures():
    """`validation/evaluation/judge-spot-check.md` / `judge-spot-check-judge.md` are the actual owner-graded
    EVAL-004a sheet and key (ledger row 11). This is the proof check 5's fix asked for: 8/10 rule-based agreement,
    kappa 0.6875, disagreements S09/S10; holistic 9/10 (S03) - and the sheet/key are never modified."""
    sheet_path = PROJECT_ROOT / "validation" / "evaluation" / "judge-spot-check.md"
    key_path = PROJECT_ROOT / "validation" / "evaluation" / "judge-spot-check-judge.md"
    before_sheet, before_key = sheet_path.read_bytes(), key_path.read_bytes()

    cases = score_spot_check.parse_owner_sheet(sheet_path.read_text(encoding="utf-8"))
    score_spot_check.check_filled(cases)
    key = score_spot_check.parse_key(key_path.read_text(encoding="utf-8"))
    records = score_spot_check.load_records_by_key(key, root=PROJECT_ROOT)
    pairs = score_spot_check.rule_based_pairs(cases, key, records)
    two = [(judge, owner) for _, judge, owner in pairs]

    agreement = score_spot_check.agreement_rate(two)
    assert (agreement["count"], agreement["n"]) == (8, 10)
    assert score_spot_check.cohens_kappa(two) == pytest.approx(0.6875)
    disagreeing = {sid for sid, judge, owner in pairs if judge != owner}
    assert disagreeing == {"S09", "S10"}

    holistic_no = {sid for sid in cases if not score_spot_check.holistic_agreement(cases[sid]["grades"])}
    assert holistic_no == {"S03"}
    assert len(cases) - len(holistic_no) == 9

    assert sheet_path.read_bytes() == before_sheet  # never edited
    assert key_path.read_bytes() == before_key
