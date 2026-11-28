"""System refusal threshold: sweep the dense-score gate over gate-off dev runs (docs/plans/gate-calibration-v3.md).

    python scripts/evaluation/gate_calibration.py --system NAME=RUN_ID[,RUN_ID ...] [--system ...] [--current 0.5417]

Each `--system` is one answer model: its gate-off runs over the dev splits (pooled; a case id may appear once). Every
run must have been made with the gate off (`threshold` <= 0 in run.json and no record with `gate_fired`), so every
case reached the LLM, and must be judged. For a threshold t the system answer of a case is simulated:
- dense top-1 < t: the gate refuses before the LLM (answerable -> false_refusal, unanswerable -> correct_refusal);
- otherwise: the recorded LLM answer with its judge label (the LLM's own refusal is the second gate layer).
Candidates: "off" and the midpoints between consecutive distinct top-1 scores of the pooled cases (rounded to 4
decimals). Rule (fixed before the runs): the smallest candidate with zero hallucinations on the unanswerable cases;
if none has zero, the smallest with the fewest. Unlabelled cases (judge missing or error) are counted as
hallucination (unanswerable) or not correct (answerable) and listed; the result is then marked PROVISIONAL.
Prints, per system: the chosen threshold, its metrics, the neighbouring candidates and the current threshold.
Decides nothing on its own: the owner sets the shipped value.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "evaluation"))

from eval_report_data import load_run  # noqa: E402

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.judge import latest_judgements  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.mapping import (  # noqa: E402
    CORRECT,
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    HALLUCINATION,
    PARTIALLY_CORRECT,
)

OFF = None  # the "gate off" candidate


class CalibrationError(ValueError):
    pass


def case_rows(runs: list[dict]) -> list[dict]:
    """One row per case: id, answerable, dense top-1 and the label of the recorded (gate-off) answer."""
    rows, seen = [], set()
    for run in runs:
        if run["manifest"]["config"].get("threshold", 0) > 0:
            raise CalibrationError(f"{run['run_id']}: threshold {run['manifest']['config']['threshold']} > 0, "
                                   "the gate was on")
        lines = run["judgement_lines"]
        versions = {line["judge_prompt_version"] for line in lines}
        if len(versions) > 1:
            raise CalibrationError(f"{run['run_id']}: several judge prompt versions {sorted(versions)}")
        judgements = latest_judgements(lines)
        version = versions.pop() if versions else ""
        for record in run["records"]:
            if record["mode"] != "full" or record["status"] != "ok":
                raise CalibrationError(f"{run['run_id']}: {record['case_id']} has no ok full-mode record")
            if record["gate_fired"]:
                raise CalibrationError(f"{run['run_id']}: gate fired on {record['case_id']}")
            if record["case_id"] in seen:
                raise CalibrationError(f"case {record['case_id']} appears in more than one run")
            seen.add(record["case_id"])
            label = scoring.answer_scores(record, scoring.find_judgement(record, judgements, version))["result"]
            rows.append({"case_id": record["case_id"], "answerable": record["answerable"],
                         "top1": record["top1_score"], "label": label})
    return rows


def candidates(rows: list[dict]) -> list[float | None]:
    scores = sorted({row["top1"] for row in rows})
    return [OFF] + [round((low + high) / 2, 4) for low, high in zip(scores, scores[1:])]


def evaluate(rows: list[dict], t: float | None) -> dict:
    labels = []
    for row in rows:
        if t is not None and row["top1"] < t:
            labels.append((row, FALSE_REFUSAL if row["answerable"] else CORRECT_REFUSAL))
        else:
            labels.append((row, row["label"]))
    answerable = [label for row, label in labels if row["answerable"]]
    unanswerable = [label for row, label in labels if not row["answerable"]]
    unlabelled = [row["case_id"] for row, label in labels if label is None]
    return {
        "t": t, "n_answerable": len(answerable), "n_unanswerable": len(unanswerable),
        "hallucination": sum(1 for label in unanswerable if label in (HALLUCINATION, None)),
        "false_refusal": sum(1 for label in answerable if label == FALSE_REFUSAL),
        "correct": sum(1 for label in answerable if label == CORRECT),
        "lenient": sum(1 for label in answerable if label in (CORRECT, PARTIALLY_CORRECT)),
        "gate_refused": sum(1 for row, _ in labels if t is not None and row["top1"] < t),
        "unlabelled": unlabelled,
    }


def choose(results: list[dict]) -> dict:
    """Smallest candidate (off first) with the fewest hallucinations; results are in candidate order."""
    fewest = min(result["hallucination"] for result in results)
    return next(result for result in results if result["hallucination"] == fewest)


def _t(t) -> str:
    return "off" if t is None else f"{t:.4f}"


def _row(result: dict, note: str = "") -> str:
    a, u = result["n_answerable"], result["n_unanswerable"]
    pct = lambda n, d: f"{n}/{d} ({n / d:.0%})" if d else "n/a"  # noqa: E731
    return (f"| {_t(result['t'])}{note} | {pct(result['hallucination'], u)} | {pct(result['false_refusal'], a)} | "
            f"{pct(result['lenient'], a)} | {pct(result['correct'], a)} | {result['gate_refused']} |")


def report(name: str, rows: list[dict], current: float | None) -> list[str]:
    cands = candidates(rows)
    results = [evaluate(rows, t) for t in cands]
    best = choose(results)
    index = results.index(best)
    lines = [f"### {name}", "",
             "| threshold | hallucination (unanswerable) | false refusal (answerable) | lenient | strict | gate refused |",
             "|---|---|---|---|---|---|"]
    shown = results[max(0, index - 2): index + 3]
    for result in shown:
        lines.append(_row(result, " **(chosen)**" if result is best else ""))
    if current is not None:
        lines.append(_row(evaluate(rows, current), " (current)"))
    if best["unlabelled"]:
        lines += ["", f"PROVISIONAL: unlabelled cases {', '.join(best['unlabelled'])} (counted as failures)."]
    return lines + [""]


def parse_system(text: str) -> tuple[str, list[str]]:
    name, sep, runs = text.partition("=")
    if not sep or not name or not runs:
        raise argparse.ArgumentTypeError(f"--system NAME=RUN[,RUN...], got {text!r}")
    return name, [run for run in runs.split(",") if run]


def main(argv: list[str] | None = None, root: Path = PROJECT_ROOT, out=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--system", type=parse_system, action="append", required=True)
    parser.add_argument("--current", type=float, help="the threshold in use, shown for comparison")
    args = parser.parse_args(argv)
    out = out or sys.stdout
    try:
        for name, run_ids in args.system:
            rows = case_rows([load_run(run_id, root) for run_id in run_ids])
            print("\n".join(report(name, rows, args.current)), file=out)
    except CalibrationError as error:
        print(f"ABORTED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
