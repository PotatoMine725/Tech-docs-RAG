"""judge_crossval.py: re-judging goes to a separate file and never touches the run's judgements.jsonl. Offline."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("judge_crossval_under_test", ROOT / "scripts" / "evaluation" / "judge_crossval.py")
crossval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crossval)


def _run_dir(root: Path, run_id: str) -> Path:
    directory = root / crossval.RESULTS / run_id
    directory.mkdir(parents=True)
    (directory / "run.json").write_text("{}", encoding="utf-8")
    (directory / "records.jsonl").write_text(json.dumps({"case_id": "Q1"}) + "\n", encoding="utf-8")
    (directory / "judgements.jsonl").write_text("ORIGINAL\n", encoding="utf-8")
    return directory


def test_run_writes_a_separate_crossval_file_and_keeps_judgements(tmp_path):
    directory = _run_dir(tmp_path, "r1")
    calls = []

    def fake_judge(argv, root):
        calls.append(argv)
        staged = root / crossval.RESULTS / "r1"
        assert not (staged / "judgements.jsonl").exists()  # the run's own verdicts are not copied to staging
        (staged / "judgements.jsonl").write_text("NEW\n", encoding="utf-8")
        return 0

    items = [{"item": "S01", "run": "r1", "case": "Q1", "owner": "correct"}]
    assert crossval.run(items, tmp_path, "m-x", estimate_only=False, judge_main=fake_judge) == 0
    assert calls == [["--run-id", "r1", "--cases", "Q1"]]
    assert (directory / "judgements.jsonl").read_text(encoding="utf-8") == "ORIGINAL\n"
    assert (directory / crossval.crossval_name("m-x")).read_text(encoding="utf-8") == "NEW\n"


def test_run_resumes_from_an_existing_crossval_file_and_estimate_writes_nothing(tmp_path):
    directory = _run_dir(tmp_path, "r1")
    (directory / crossval.crossval_name("m-x")).write_text("EARLIER\n", encoding="utf-8")
    seen = []

    def fake_judge(argv, root):
        seen.append((root / crossval.RESULTS / "r1" / "judgements.jsonl").read_text(encoding="utf-8"))
        return 0

    items = [{"item": "S01", "run": "r1", "case": "Q1", "owner": "correct"}]
    crossval.run(items, tmp_path, "m-x", estimate_only=True, judge_main=fake_judge)
    assert seen == ["EARLIER\n"]
    assert (directory / crossval.crossval_name("m-x")).read_text(encoding="utf-8") == "EARLIER\n"


def test_summary_counts_agreement_only_over_labelled_crossval_items():
    rows = [{"owner": "hallucination", "judge": "hallucination", "crossval": "hallucination"},
            {"owner": "hallucination", "judge": "correct_refusal", "crossval": None},
            {"owner": "correct", "judge": "correct", "crossval": "partially_correct"}]
    counts = crossval.summary(rows)
    assert counts["items"] == 3 and counts["owner=judge"] == 2 and counts["crossval labelled"] == 2
    assert counts["owner=crossval"] == 1 and counts["judge=crossval"] == 1
