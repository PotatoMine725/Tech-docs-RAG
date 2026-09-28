"""EVAL-003c: `scripts/evaluation/make_tables.py`. Offline, made-up records and question data (no eval-set content)."""
import io
import json

from scripts.evaluation import make_tables
from tests.eval_report_fakes import (
    judgement_line,
    span_dict,
    write_judgements,
    write_manifest,
    write_pricing,
    write_records,
    write_spans_file,
)
from tests.judge_fakes import answer_verdict, make_record


# --- marker replacement: idempotent, text outside untouched, missing marker appended -----------------------

def test_a_new_marker_is_appended_as_a_new_section():
    text = "# Report\n\nSome hand-written intro.\n"
    out = make_tables.replace_or_append_section(text, "retrieval", "Retrieval metrics", "body v1")
    assert "Some hand-written intro." in out
    assert "<!-- AUTO:retrieval -->\nbody v1\n<!-- /AUTO:retrieval -->" in out
    assert out.index("Some hand-written intro.") < out.index("<!-- AUTO:retrieval -->")


def test_replacing_an_existing_marker_leaves_everything_else_untouched():
    text = ("# Report\n\nIntro kept as is.\n\n## Retrieval metrics\n\n<!-- AUTO:retrieval -->\nold body\n"
           "<!-- /AUTO:retrieval -->\n\nTrailing note kept too.\n")
    out = make_tables.replace_or_append_section(text, "retrieval", "Retrieval metrics", "new body")
    assert "Intro kept as is." in out and "Trailing note kept too." in out
    assert "old body" not in out and "<!-- AUTO:retrieval -->\nnew body\n<!-- /AUTO:retrieval -->" in out


def test_replacing_is_idempotent_running_it_three_times_gives_the_same_result_as_once():
    text = "# Report\n"
    once = make_tables.replace_or_append_section(text, "cost", "Cost", "body")
    twice = make_tables.replace_or_append_section(once, "cost", "Cost", "body")
    thrice = make_tables.replace_or_append_section(twice, "cost", "Cost", "body")
    assert once == twice == thrice
    assert once.count("<!-- AUTO:cost -->") == 1  # never duplicated


def test_a_marker_with_special_regex_characters_in_the_body_is_handled_safely():
    """A judge reason or answer text can contain `\\`, `[]`, `$` etc.; the replacement must be literal, not a regex
    template (a naive `re.sub(pattern, body)` would choke on backreferences like `\\1` inside `body`)."""
    text = make_tables.replace_or_append_section("# R\n", "cost", "Cost", "first")
    tricky = r"a \1 backslash, a $100 estimate, and [brackets]"
    out = make_tables.replace_or_append_section(text, "cost", "Cost", tricky)
    assert tricky in out


def test_ensure_placeholder_never_overwrites_an_existing_section():
    """`score_spot_check.py` fills `judge_agreement`; a later `make_tables.py` run must never clobber that."""
    text = make_tables.replace_or_append_section("# R\n", "judge_agreement", "Judge spot-check agreement", "REAL SCORE")
    out = make_tables.ensure_placeholder_section(text, "judge_agreement", "Judge spot-check agreement", "placeholder")
    assert "REAL SCORE" in out and "placeholder" not in out


def test_ensure_placeholder_adds_it_once_when_absent():
    out = make_tables.ensure_placeholder_section("# R\n", "judge_agreement", "Judge spot-check agreement", "placeholder")
    assert "placeholder" in out and out.count("<!-- AUTO:judge_agreement -->") == 1


# --- CSV: at least the brief's 5 columns, mapped as evaluation-dataset-design.md §18 says -------------------

def test_csv_rows_have_the_briefs_five_columns_correctly_mapped():
    record = make_record(1, answer="The answer [1].", cited=(1,))
    row = {"answer": {"result": "correct"}}
    rows = make_tables.csv_rows([(record, row)])
    assert len(rows) == 1
    csv_row = rows[0]
    for column in ("question", "expected_answer", "expected_source", "generated_answer", "result"):
        assert column in csv_row
    assert csv_row["question"] == record["question"]
    assert csv_row["expected_answer"] == record["expected_answer"]
    assert csv_row["expected_source"] == "01 Doc > Part 1"  # source_id + heading path (§18)
    assert csv_row["generated_answer"] == "The answer [1]."
    assert csv_row["result"] == "correct"
    assert csv_row["case_id"] == "Q-TEST-001" and csv_row["arm"] == "A" and csv_row["language"] == "en"
    assert csv_row["citations"] == "[1] 01 Doc > Part 1"
    assert csv_row["latency_total_ms"] is None  # the fixture record never set a latency


def test_csv_row_of_a_record_with_no_generated_answer_has_empty_not_none_strings():
    record = make_record(1, answer=None, insufficient=True, cited=())
    row = {"answer": None}
    csv_row = make_tables.csv_rows([(record, row)])[0]
    assert csv_row["generated_answer"] == "" and csv_row["result"] == "" and csv_row["citations"] == ""


# --- summary rendering degrades gracefully on an empty group (no KeyError) ----------------------------------

def test_retrieval_table_on_an_empty_summary_shows_zero_n_not_a_key_error():
    empty_summary = {"duplicate_rule_changed": {"n": 0, "count": 0, "cases": []}}
    table = make_tables.retrieval_table(empty_summary)
    assert "source_hit@5" in table and "n=0" in table


# --- end to end: one full run through main(), determinism, real scoring ------------------------------------

def build_fixture(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))  # scored: Q-TEST-001, source 01, span covers it
    r2 = make_record(2, answerable=False, insufficient=True, cited=())  # corpus-insufficient, bare refusal
    write_records(directory, [r1, r2])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict())])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})
    write_pricing(tmp_path, model="test-answer-model")
    return directory


def test_main_writes_report_summary_and_csv_from_a_fake_run(tmp_path):
    build_fixture(tmp_path)
    out_path = tmp_path / "report.md"
    out, err = io.StringIO(), io.StringIO()
    code = make_tables.main(["--runs", "run-1", "--out", str(out_path)], root=tmp_path, out=out, err=err)
    assert code == make_tables.EXIT_OK, err.getvalue()

    report = out_path.read_text(encoding="utf-8")
    for name in make_tables.SECTION_ORDER:
        assert f"<!-- AUTO:{name} -->" in report and f"<!-- /AUTO:{name} -->" in report
    assert "<!-- AUTO:judge_agreement -->" in report and "Owner judge spot-check not yet run" in report
    assert "Q-TEST-001" in report  # per_case table

    summary_path = tmp_path / "data" / "evaluation" / "results" / "summary-run-1.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["run_ids"] == ["run-1"]
    assert summary["breakdown"]["overall"]["retrieval"]["section_hit@5"]["value"] == 1.0
    assert summary["breakdown"]["overall"]["answer"]["labels"]["correct"] == 1
    assert summary["breakdown"]["overall"]["answer"]["labels"]["correct_refusal"] == 1

    csv_path = tmp_path / "data" / "evaluation" / "results" / "eval-table-run-1.csv"
    assert csv_path.exists()
    header = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert header.split(",") == list(make_tables.CSV_COLUMNS)


def test_running_main_twice_on_the_same_fixture_is_byte_identical(tmp_path):
    build_fixture(tmp_path)
    out_path = tmp_path / "report.md"
    for _ in range(2):
        code = make_tables.main(["--runs", "run-1", "--out", str(out_path)], root=tmp_path,
                                out=io.StringIO(), err=io.StringIO())
        assert code == make_tables.EXIT_OK
    first = out_path.read_bytes()
    code = make_tables.main(["--runs", "run-1", "--out", str(out_path)], root=tmp_path,
                            out=io.StringIO(), err=io.StringIO())
    assert code == make_tables.EXIT_OK
    assert out_path.read_bytes() == first
    summary_path = tmp_path / "data" / "evaluation" / "results" / "summary-run-1.json"
    first_summary = summary_path.read_bytes()
    make_tables.main(["--runs", "run-1", "--out", str(out_path)], root=tmp_path, out=io.StringIO(), err=io.StringIO())
    assert summary_path.read_bytes() == first_summary


def test_a_missing_run_aborts_instead_of_crashing(tmp_path):
    out, err = io.StringIO(), io.StringIO()
    code = make_tables.main(["--runs", "no-such-run"], root=tmp_path, out=out, err=err)
    assert code == make_tables.EXIT_ABORTED and "no-such-run" in err.getvalue()


# --- judge prompt-version drift guard (VERIFY EVAL-003c check 2/4) -------------------------------------------

def test_prompt_version_mismatches_ignores_a_run_with_no_judgements():
    run = {"run_id": "r1", "judgement_lines": []}
    assert make_tables.prompt_version_mismatches([run], "judge_v1") == []


def test_prompt_version_mismatches_flags_a_run_judged_with_a_different_version():
    run = {"run_id": "r1", "judgement_lines": [
        {"case_id": "c", "arm": "A", "answer_sha256": "h", "judge_prompt_version": "judge_v0"}]}
    assert make_tables.prompt_version_mismatches([run], "judge_v1") == [("r1", "judge_v0")]


def test_prompt_version_mismatches_disabled_when_expected_is_none():
    run = {"run_id": "r1", "judgement_lines": [
        {"case_id": "c", "arm": "A", "answer_sha256": "h", "judge_prompt_version": "judge_v0"}]}
    assert make_tables.prompt_version_mismatches([run], None) == []


def test_main_aborts_when_a_run_was_judged_with_an_unexpected_prompt_version(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))
    write_records(directory, [r1])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict(), prompt_version="judge_v2")])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})
    write_pricing(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = make_tables.main(["--runs", "run-1", "--judge-prompt-version", "judge_v1"], root=tmp_path, out=out, err=err)
    assert code == make_tables.EXIT_ABORTED
    assert "judge_v1" in err.getvalue() and "judge_v2" in err.getvalue() and "run-1" in err.getvalue()


def test_main_accepts_an_explicit_judge_prompt_version_matching_the_run(tmp_path):
    build_fixture(tmp_path)  # judged with judge_v1 (the default in judgement_line)
    out, err = io.StringIO(), io.StringIO()
    code = make_tables.main(["--runs", "run-1", "--judge-prompt-version", "judge_v1"], root=tmp_path, out=out, err=err)
    assert code == make_tables.EXIT_OK, err.getvalue()


# --- caption/table content (VERIFY EVAL-003c check 3/6): kills the surviving mutants a3, b2, b3 -----------------

def test_base_caption_names_every_spans_unavailable_case_id_arm():
    rows = [{"case_id": "Q-A", "arm": "A", "spans_unavailable": True},
           {"case_id": "Q-B", "arm": "B", "spans_unavailable": False},
           {"case_id": "Q-C", "arm": "A", "spans_unavailable": True}]
    runs = [{"run_id": "run-1", "split": "eval", "manifest": {"config": {"arm": "A", "mode": "full"}}, "records": []}]
    caption = make_tables.base_caption(runs, rows)
    assert "Q-A:A" in caption and "Q-C:A" in caption and "Q-B:B" not in caption


def test_base_caption_flags_a_dev_split_run():
    runs = [{"run_id": "run-1", "split": "dev", "manifest": {"config": {"arm": "A", "mode": "full"}}, "records": []}]
    caption = make_tables.base_caption(runs, [])
    assert "run-1" in caption and "dev split" in caption and "dry-run" in caption


def test_every_section_caption_names_the_excluded_case(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="full", split="dev")
    r1 = make_record(1, answerable=True, cited=(1,))  # covered: Q-TEST-001 is in the spans file below
    r2 = make_record(2, answerable=True, cited=(1,))  # uncovered: Q-TEST-002 is not
    write_records(directory, [r1, r2])
    write_judgements(directory, [judgement_line(r1, "answer", answer_verdict()),
                                 judgement_line(r2, "answer", answer_verdict())])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})
    write_pricing(tmp_path)
    out_path = tmp_path / "report.md"
    code = make_tables.main(["--runs", "run-1", "--out", str(out_path)], root=tmp_path,
                            out=io.StringIO(), err=io.StringIO())
    assert code == make_tables.EXIT_OK
    report = out_path.read_text(encoding="utf-8")
    for name in make_tables.SECTION_ORDER:
        start = report.index(f"<!-- AUTO:{name} -->")
        end = report.index(f"<!-- /AUTO:{name} -->", start)
        assert "Q-TEST-002:A" in report[start:end], f"{name} section is missing the excluded case"


def test_per_case_table_places_result_and_citation_auto_class_in_the_correct_columns():
    record = {"case_id": "Q-X", "arm": "A", "mode": "full", "language": "en", "status": "ok",
             "latency_ms": {"total": 123.4}, "gate_fired": False}
    row = {"split": "eval", "answer": {"result": "correct", "points_covered": 1.0},
          "citation": {"auto_class": "citation_missing"}, "spans_unavailable": False}
    table = make_tables.per_case_table([(record, row)])
    headers = [h.strip() for h in table.splitlines()[0].strip("|").split("|")]
    cells = [c.strip() for c in table.splitlines()[2].strip("|").split("|")]
    row_by_header = dict(zip(headers, cells))
    assert row_by_header["result"] == "correct"
    assert row_by_header["citation_auto_class"] == "citation_missing"


def test_retrieval_table_puts_lenient_in_its_column_and_strict_in_its_own():
    summary = {"duplicate_rule_changed": {"n": 0, "count": 0, "cases": []},
              "source_hit@1": {"n": 2, "value": 1.0}, "source_hit@1:strict": {"n": 2, "value": 0.5}}
    table = make_tables.retrieval_table(summary)
    lines = table.splitlines()
    headers = [h.strip() for h in lines[0].strip("|").split("|")]
    cells = [c.strip() for c in lines[2].strip("|").split("|")]  # first data row: source_hit@1
    row_by_header = dict(zip(headers, cells))
    assert row_by_header["metric"] == "source_hit@1"
    assert row_by_header["lenient (headline)"] == "1.000 (n=2)"
    assert row_by_header["strict"] == "0.500 (n=2)"


def test_main_never_aborts_on_a_retrieval_mode_run_with_no_judgements(tmp_path):
    directory = write_manifest(tmp_path, "run-1", arm="A", mode="retrieval", split="dev")
    write_records(directory, [make_record(1, answerable=True, cited=(1,), mode="retrieval")])
    write_spans_file(tmp_path, {"Q-TEST-001": {"answerable": True, "slots": {"S1": [span_dict("01", "Doc > Part 1")]}}})
    write_pricing(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = make_tables.main(["--runs", "run-1", "--judge-prompt-version", "some-other-version"], root=tmp_path,
                            out=out, err=err)
    assert code == make_tables.EXIT_OK, err.getvalue()
