"""EVAL-003c: `scripts/evaluation/score_spot_check.py`. Offline, made-up data (no eval-set content)."""
import io

import pytest

from scripts.evaluation import make_spot_check, score_spot_check
from tests.eval_report_fakes import judgement_line, span_dict, write_judgements, write_manifest, write_records, write_spans_file
from tests.judge_fakes import answer_verdict, make_record

SHEET = """# Judge spot-check — run-1
<!-- run_id: run-1 -->

Preamble text.

## Q-TEST-001 (arm A, en)

- **Question:** What does part 1 say?
- **Expected answer:** Part 1 says so.
- **Generated answer:** Part 1 says so [1].
- **Cited excerpts:**
  - [1] #01 Doc > Part 1 — ## Static classes A static class ...
- **Judge result:** correct
- **Judge reason:** Fine.
- **human_result:** {q1}
- **human_note:** {n1}

---

## Q-TEST-002 (arm A, vi)

- **Question:** Phần 2 nói gì?
- **Expected answer:** Part 2 says so.
- **Generated answer:** Part 2 says so [1].
- **Cited excerpts:**
  - [1] #01 Doc > Part 2 — text
- **Judge result:** correct
- **Judge reason:** Fine.
- **human_result:** {q2}
- **human_note:** {n2}
"""


def sheet(q1="", n1="", q2="", n2=""):
    return SHEET.format(q1=q1, n1=n1, q2=q2, n2=n2)


# --- parsing: the embedded "## Static classes" mid-line never splits a case in two ---------------------------

def test_parse_sheet_finds_exactly_two_cases_despite_a_stray_heading_mid_line():
    cases = score_spot_check.parse_sheet(sheet())
    assert [case["case_id"] for case in cases] == ["Q-TEST-001", "Q-TEST-002"]
    assert cases[0]["arm"] == "A" and cases[0]["language"] == "en"
    assert cases[0]["Judge result"] == "correct"


def test_run_id_from_sheet_reads_the_marker():
    assert score_spot_check.run_id_from_sheet(sheet()) == "run-1"


# --- refuses while any human_result is blank ------------------------------------------------------------------

def test_check_filled_raises_naming_every_blank_case():
    cases = score_spot_check.parse_sheet(sheet(q1="", q2="partially_correct"))
    with pytest.raises(score_spot_check.SpotCheckError, match="Q-TEST-001"):
        score_spot_check.check_filled(cases)


def test_check_filled_raises_on_an_unknown_label():
    cases = score_spot_check.parse_sheet(sheet(q1="sort-of", q2="correct"))
    with pytest.raises(score_spot_check.SpotCheckError, match="sort-of"):
        score_spot_check.check_filled(cases)


def test_check_filled_passes_when_every_case_has_a_known_label():
    cases = score_spot_check.parse_sheet(sheet(q1="correct", q2="partially_correct"))
    score_spot_check.check_filled(cases)  # does not raise


# --- agreement, kappa (hand-computed 2x2), confusion matrix, disagreements -----------------------------------

def test_agreement_rate_on_full_agreement():
    assert score_spot_check.agreement_rate([("correct", "correct"), ("incorrect", "incorrect")]) == \
        {"n": 2, "count": 2, "value": 1.0}


def test_cohens_kappa_hand_computed_two_by_two_example():
    """4 items, 2 categories: judge=[A,A,B,B], human=[A,B,B,B].
    p_o = 3/4 = 0.75 (agree on items 1, 3, 4).
    p_e = P(judge=A)*P(human=A) + P(judge=B)*P(human=B) = 0.5*0.25 + 0.5*0.75 = 0.5.
    kappa = (0.75 - 0.5) / (1 - 0.5) = 0.5.
    """
    pairs = [("A", "A"), ("A", "B"), ("B", "B"), ("B", "B")]
    assert score_spot_check.agreement_rate(pairs)["value"] == pytest.approx(0.75)
    assert score_spot_check.cohens_kappa(pairs) == pytest.approx(0.5)


def test_cohens_kappa_is_zero_when_agreement_equals_chance():
    """judge=[A,A,B,B], human=[A,B,A,B]: po=0.5; judge and human are each 50/50 and independent, pe=0.5 -> kappa=0."""
    pairs = [("A", "A"), ("A", "B"), ("B", "A"), ("B", "B")]
    assert score_spot_check.cohens_kappa(pairs) == pytest.approx(0.0)


def test_cohens_kappa_of_no_pairs_is_none():
    assert score_spot_check.cohens_kappa([]) is None


def test_confusion_matrix_counts_judge_rows_against_human_columns():
    pairs = [("correct", "correct"), ("correct", "partially_correct"), ("incorrect", "incorrect")]
    labels, matrix = score_spot_check.confusion_matrix(pairs)
    assert labels == ["correct", "incorrect", "partially_correct"]
    assert matrix["correct"]["correct"] == 1
    assert matrix["correct"]["partially_correct"] == 1
    assert matrix["incorrect"]["incorrect"] == 1
    assert matrix["incorrect"]["correct"] == 0


def test_disagreements_lists_only_the_cases_where_human_differs_from_judge():
    cases = score_spot_check.parse_sheet(sheet(q1="correct", n1="", q2="partially_correct", n2="minor nit"))
    bad = score_spot_check.disagreements(cases)
    assert [case["case_id"] for case in bad] == ["Q-TEST-002"]


# --- end to end: refuses on a blank sheet, writes the report section on a filled one, never touches other markers

def build_run(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))
    write_records(directory, [r1])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict())])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})


def test_main_refuses_on_a_blank_sheet_and_writes_nothing(tmp_path):
    sheet_path = tmp_path / "sheet.md"
    sheet_path.write_text(sheet(), encoding="utf-8")
    report_path = tmp_path / "report.md"
    report_path.write_text("# Report\nkeep me\n", encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    code = score_spot_check.main([str(sheet_path), "--out", str(report_path)], root=tmp_path, out=out, err=err)
    assert code == score_spot_check.EXIT_ABORTED
    assert report_path.read_text(encoding="utf-8") == "# Report\nkeep me\n"  # untouched


def test_main_scores_a_filled_sheet_and_fills_the_marker_without_touching_the_rest(tmp_path):
    sheet_path = tmp_path / "sheet.md"
    sheet_path.write_text(sheet(q1="correct", q2="partially_correct", n2="close call"), encoding="utf-8")
    report_path = tmp_path / "report.md"
    report_path.write_text(
        "# Report\n\nBefore.\n\n<!-- AUTO:judge_agreement -->\nplaceholder\n<!-- /AUTO:judge_agreement -->\n\nAfter.\n",
        encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    code = score_spot_check.main([str(sheet_path), "--out", str(report_path)], root=tmp_path, out=out, err=err)
    assert code == score_spot_check.EXIT_OK, err.getvalue()
    text = report_path.read_text(encoding="utf-8")
    assert "Before." in text and "After." in text and "placeholder" not in text
    assert "Q-TEST-002" in text and "close call" in text
    assert "0.500" in text  # agreement 1/2


def test_running_score_spot_check_twice_on_the_same_inputs_is_byte_identical(tmp_path):
    sheet_path = tmp_path / "sheet.md"
    sheet_path.write_text(sheet(q1="correct", q2="correct"), encoding="utf-8")
    report_path = tmp_path / "report.md"
    score_spot_check.main([str(sheet_path), "--out", str(report_path)], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    first = report_path.read_bytes()
    score_spot_check.main([str(sheet_path), "--out", str(report_path)], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert report_path.read_bytes() == first
