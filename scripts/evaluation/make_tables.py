"""EVAL-003c: turn EVAL-003b's scoring functions into report tables, a summary JSON and a per-run CSV.

    python scripts/evaluation/make_tables.py --runs RUN_ID [RUN_ID ...] [--out PATH]

Reads `data/evaluation/results/<run_id>/` (`run.json`, `records.jsonl`, `judgements.jsonl`) for every run id given and
computes every number from them, through `application/evaluation/scoring.py` and `metrics/*.py` (EVAL-003b) - never
from a hand-typed value. Writes:

- Markdown tables into `--out` (default `docs/reports/epics/EPIC-05-evaluation.md`, created if it does not exist)
  between `<!-- AUTO:<name> --> ... <!-- /AUTO:<name> -->` markers: `retrieval`, `answer`, `refusal`, `citation`,
  `latency`, `cost`, `per_language`, `parallel`, `per_case`. Text outside a marker is never touched; a marker this
  file does not yet have is appended as a new section instead of failing. A `judge_agreement` placeholder section is
  added once (never overwritten here) for `score_spot_check.py` to fill in later.
- `data/evaluation/results/summary-<run ids joined by "-">.json` with every number the tables show.
- `data/evaluation/results/eval-table-<run_id>.csv` per run, with the brief's 5 columns (question, expected_answer,
  expected_source, generated_answer, result) plus case_id, arm, language, citations, latency_total_ms
  (evaluation-dataset-design.md §18).

Deterministic: every collection this script renders is sorted first (case_id/arm/mode order, or a fixed metric-name
order), so running it twice on the same run folders byte-for-byte reproduces the same tables, JSON and CSV.

Zero Gemini requests: offline, reads only what earlier runs already wrote to disk.
Does not run the evaluation (EVAL-003a/EVAL-004) and does not write analysis text - tables, CSV and JSON only.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):  # "src" for knowledge_assistant.*; the root for scripts.*
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.latency import summarize_latency  # noqa: E402
from knowledge_assistant.core.exceptions import EvaluationError  # noqa: E402

from scripts.evaluation.eval_report_data import (  # noqa: E402
    build_chunk_indexes,
    gate_refused_answerable,
    load_pricing,
    load_runs,
    load_spans_by_case,
    score_run_pairs,
)

DEFAULT_OUT = Path("docs/reports/epics/EPIC-05-evaluation.md")
EXIT_OK, EXIT_ABORTED = 0, 3

SECTION_TITLES = {
    "retrieval": "Retrieval metrics",
    "answer": "Answer metrics",
    "refusal": "Refusal metrics",
    "citation": "Citation metrics",
    "latency": "Latency",
    "cost": "Cost (estimate)",
    "per_language": "Per language",
    "parallel": "Parallel EN/VI subset",
    "per_case": "Per case",
}
SECTION_ORDER = ("retrieval", "answer", "refusal", "citation", "latency", "cost", "per_language", "parallel", "per_case")
JUDGE_AGREEMENT_NAME = "judge_agreement"
JUDGE_AGREEMENT_TITLE = "Judge spot-check agreement (owner)"
JUDGE_AGREEMENT_PLACEHOLDER = (
    "*(Owner judge spot-check not yet run. After the owner fills `human_result` in "
    "`docs/reviews/evaluation/judge-spot-check-<run>.md`, run `scripts/evaluation/score_spot_check.py <file>` to "
    "fill this section: agreement %, Cohen's kappa, the confusion matrix and the list of disagreements.)*"
)
CSV_COLUMNS = ("question", "expected_answer", "expected_source", "generated_answer", "result",
              "case_id", "arm", "language", "citations", "latency_total_ms")


# --- rendering helpers (pure: dict/list in, markdown string out) -----------------------------------------------

def _fmt(value: float, digits: int = 3) -> str:
    return "–" if value is None else f"{value:.{digits}f}"


def _rate_cell(rate: dict) -> str:
    return "– (n=0)" if rate["value"] is None else f"{rate['value']:.3f} ({rate['count']}/{rate['n']})"


def _mean_cell(mean: dict) -> str:
    return "– (n=0)" if mean["value"] is None else f"{mean['value']:.3f} (n={mean['n']})"


def md_table(headers: tuple, rows: list[tuple]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def run_descriptions(runs: list[dict]) -> str:
    return "; ".join(f"`{run['run_id']}` (arm {run['manifest']['config']['arm']}, "
                     f"mode {run['manifest']['config']['mode']}, split {run['split']}, {len(run['records'])} record(s))"
                     for run in runs)


def base_caption(runs: list[dict], rows: list[dict]) -> str:
    """Every table caption starts here: run ids, n, and what was excluded and why."""
    excluded_spans = sorted({f"{row['case_id']}:{row['arm']}" for row in rows if row["spans_unavailable"]})
    dev_runs = sorted({run["run_id"] for run in runs if run["split"] == "dev"})
    parts = [f"Runs: {run_descriptions(runs)}. Total scored records: {len(rows)}."]
    if excluded_spans:
        parts.append("Excluded from retrieval and citation scoring (answerable, but outside "
                     f"`expected-spans-v1.json`, which covers the eval split only): {', '.join(excluded_spans)}.")
    if dev_runs:
        parts.append(f"**{', '.join(dev_runs)} use the dev split - dry-run/tooling data only, never reported as "
                     "evaluation results (`evaluation-spec.md` § Dataset mix).**")
    return " ".join(parts)


_NO_MEAN = {"n": 0, "value": None}


def _mean_of(summary: dict, key: str) -> dict:
    """`summarize_retrieval` only has metric keys when at least one row was scored (always has
    `duplicate_rule_changed`); a group with none (e.g. every answerable record excluded for missing spans) needs a
    zero-record placeholder instead of a KeyError."""
    return summary.get(key, _NO_MEAN)


def retrieval_table(summary: dict) -> str:
    rows = []
    for k in (1, 3, 5):
        rows.append((f"source_hit@{k}", _mean_cell(_mean_of(summary, f"source_hit@{k}")), _mean_cell(_mean_of(summary, f"source_hit@{k}:strict"))))
        rows.append((f"section_hit@{k}", _mean_cell(_mean_of(summary, f"section_hit@{k}")), _mean_cell(_mean_of(summary, f"section_hit@{k}:strict"))))
    rows.append(("mrr", _mean_cell(_mean_of(summary, "mrr")), _mean_cell(_mean_of(summary, "mrr:strict"))))
    rows.append(("source_mrr", _mean_cell(_mean_of(summary, "source_mrr")), _mean_cell(_mean_of(summary, "source_mrr:strict"))))
    rows.append(("slot_fraction@5", _mean_cell(_mean_of(summary, "slot_fraction@5")), "–"))
    rows.append(("source_slot_fraction@5", _mean_cell(_mean_of(summary, "source_slot_fraction@5")), "–"))
    for k in (1, 3, 5):
        rows.append((f"evidence_hit@{k}", _mean_cell(_mean_of(summary, f"evidence_hit@{k}")), "–"))
        rows.append((f"any_evidence_hit@{k}", _mean_cell(_mean_of(summary, f"any_evidence_hit@{k}")), "–"))
    rows.append(("evidence_hit_via_alternate_only@5", _mean_cell(_mean_of(summary, "evidence_hit_via_alternate_only@5")), "–"))
    table = md_table(("metric", "lenient (headline)", "strict"), rows)
    dup = summary["duplicate_rule_changed"]
    alt = _mean_of(summary, "evidence_hit_via_alternate_only@5")
    notes = [
        f"duplicate rule changed {dup['count']} of {dup['n']} scored case x arm value(s)"
        + (f": {', '.join(dup['cases'])}" if dup["cases"] else "") + ".",
        "evidence_hit_via_alternate_only@5 cases: " + (", ".join(alt.get("cases", [])) or "(none)") + ".",
        "corpus-insufficient cases have no expected spans and are excluded from every row above.",
    ]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def answer_table(summary: dict) -> str:
    rows = [
        ("accuracy", _rate_cell(summary["accuracy"])),
        ("lenient_accuracy", _rate_cell(summary["lenient_accuracy"])),
        ("groundedness_rate", _rate_cell(summary["groundedness_rate"])),
        ("points_covered_mean", _mean_cell(summary["points_covered_mean"])),
        ("false_refusal_rate", _rate_cell(summary["false_refusal_rate"])),
    ]
    table = md_table(("metric (denominator: labelled answerable records)", "value"), rows)
    labels = summary["labels"]
    label_line = ", ".join(f"{name}={labels[name]}" for name in ("correct", "partially_correct", "incorrect", "false_refusal"))
    notes = [
        f"labels (answerable): {label_line}.",
        "runner-error records (no answer to label; excluded from every denominator in this report): "
        + (", ".join(summary["runner_errors"]) or "(none)") + ".",
        "unlabelled records (judge missing or judge_error; excluded from every denominator in this report): "
        + (", ".join(summary["unlabelled"]) or "(none)") + ".",
    ]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def refusal_table(summary: dict) -> str:
    rows = [("correct_refusal_rate", _rate_cell(summary["correct_refusal_rate"])),
            ("hallucination_rate", _rate_cell(summary["hallucination_rate"]))]
    table = md_table(("metric (denominator: labelled unanswerable/corpus-insufficient records)", "value"), rows)
    labels = summary["labels"]
    notes = [
        f"labels (unanswerable): correct_refusal={labels['correct_refusal']}, hallucination={labels['hallucination']}.",
        "runner-error and unlabelled records are listed once, in the answer table above (the list covers both "
        "answerable and unanswerable records).",
    ]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def citation_table(summary: dict) -> str:
    rows = [
        ("presence_rate", _rate_cell(summary["presence_rate"])),
        ("source_precision", _mean_cell(summary["source_precision"])),
        ("section_precision", _mean_cell(summary["section_precision"])),
        (f"support_rate (judge support check, n={summary['judge_class_n']})", _mean_cell(summary["support_rate"])),
    ]
    table = md_table((f"metric (denominator: answered answerable records, n={summary['answered']})", "value"), rows)
    auto, judge = summary["auto_class"], summary["judge_class"]
    notes = [
        "auto_class (automatic span check): " + ", ".join(f"{k}={auto[k]}" for k in scoring.CITATION_CLASSES) + ".",
        f"judge_class (judge support check, n={summary['judge_class_n']}): "
        + ", ".join(f"{k}={judge[k]}" for k in scoring.CITATION_CLASSES) + ".",
        f"related_citation_count (citations on an insufficient answer; counted only, not scored): "
        f"{summary['related_citation_count']}.",
        f"answered_unanswerable_with_citations (diagnostic, not scored): {summary['answered_unanswerable_with_citations']}.",
    ]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def _stage_rows(block: dict, label: str) -> list[tuple]:
    rows = []
    for stage, stats in block["stages"].items():
        if stats["n"] == 0:
            continue
        rows.append((f"{label} {stage}", str(stats["n"]), _fmt(stats["mean"], 1), _fmt(stats["p50"], 1),
                     _fmt(stats["p95"], 1), _fmt(stats["max"], 1)))
    return rows


def latency_table(latency: dict, judge_latency: dict) -> str:
    rows = (_stage_rows(latency["main"], "main") + _stage_rows(latency["retried_or_fallback"], "retried/fallback")
           + _stage_rows(judge_latency["main"], "judge main")
           + _stage_rows(judge_latency["retried_or_fallback"], "judge retried/fallback"))
    table = md_table(("stage", "n", "mean_ms", "p50_ms", "p95_ms", "max_ms"), rows) if rows else "(no timed records)"
    notes = [
        f"percentile method: {latency['method']} (`evaluation-spec.md` § Latency): no interpolation, every "
        "percentile is a value that was actually measured.",
        f"answer calls: {latency['main']['count']} clean record(s) (retry_count==0, no fallback model); "
        f"retried/fallback: {latency['retried_or_fallback']['count']}.",
        f"judge calls: {judge_latency['main']['count']} clean call(s); "
        f"retried/fallback: {judge_latency['retried_or_fallback']['count']}.",
    ]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def cost_table(cost: dict) -> str:
    rows = []
    for stage, data in cost["stages"].items():
        estimate = data["estimate"]
        usd = f"${estimate['usd']:.4f}" if estimate["usd"] is not None else f"n/a ({estimate['reason']})"
        rows.append((stage, str(data["calls"]), ", ".join(data["models"]) or "(none)", str(data["prompt_tokens"]),
                    str(data["output_tokens"]), str(data["thoughts_tokens"]), usd))
    table = md_table(("stage", "calls", "models", "prompt_tokens", "output_tokens", "thoughts_tokens", "estimate"),
                     rows) if rows else "(no priced calls)"
    source = cost.get("pricing_source") or {}
    notes = [cost["note"], f"pricing source: {source.get('url', 'n/a')} (retrieved {source.get('retrieved', 'n/a')})."]
    return table + "\n\n" + "\n".join(f"- {note}" for note in notes)


def _condensed_row(label: str, summary: dict) -> tuple:
    retrieval, answer = summary["retrieval"], summary["answer"]
    empty_mean = {"n": 0, "value": None}
    return (label, str(summary["records"]), _rate_cell(answer["accuracy"]), _rate_cell(answer["lenient_accuracy"]),
            _rate_cell(answer["correct_refusal_rate"]), _rate_cell(answer["hallucination_rate"]),
            _mean_cell(retrieval.get("source_hit@5", empty_mean)), _mean_cell(retrieval.get("section_hit@5", empty_mean)))


def condensed_table(groups: list[tuple]) -> str:
    headers = ("group", "records", "accuracy", "lenient_accuracy", "correct_refusal_rate", "hallucination_rate",
              "source_hit@5 (lenient)", "section_hit@5 (lenient)")
    return md_table(headers, [_condensed_row(label, summary) for label, summary in groups])


def per_language_table(breakdown: dict) -> str:
    return condensed_table([(f"language={lang}", summary) for lang, summary in breakdown["language"].items()])


def parallel_table(breakdown: dict) -> str:
    return condensed_table([("overall", breakdown["overall"]), ("parallel EN/VI subset", breakdown["parallel"])])


def per_case_table(pairs: list[tuple]) -> str:
    ordered = sorted(pairs, key=lambda pair: (pair[0]["case_id"], pair[0]["arm"], pair[0]["mode"]))
    rows = []
    for record, row in ordered:
        answer, citation = row.get("answer") or {}, row.get("citation") or {}
        points_covered = answer.get("points_covered")
        latency_total = record["latency_ms"].get("total")
        gate_fired = record.get("gate_fired")
        rows.append((
            record["case_id"], record["arm"], record["mode"], row["split"], record["language"], record["status"],
            answer.get("result") or "–", _fmt(points_covered) if points_covered is not None else "–",
            citation.get("auto_class") or "–",
            "yes" if gate_fired else ("no" if gate_fired is not None else "–"),
            _fmt(latency_total, 1) if latency_total is not None else "–",
            "yes" if row["spans_unavailable"] else "no",
        ))
    headers = ("case_id", "arm", "mode", "split", "language", "status", "result", "points_covered",
              "citation_auto_class", "gate_fired", "latency_total_ms", "spans_unavailable")
    return md_table(headers, rows) if rows else "(no records)"


# --- marker replacement (text outside markers, and markers not listed here, are never touched) -----------------

def _marker_pattern(name: str) -> re.Pattern:
    return re.compile(re.escape(f"<!-- AUTO:{name} -->") + r".*?" + re.escape(f"<!-- /AUTO:{name} -->"), re.DOTALL)


def replace_or_append_section(text: str, name: str, title: str, body: str) -> str:
    block = f"<!-- AUTO:{name} -->\n{body}\n<!-- /AUTO:{name} -->"
    pattern = _marker_pattern(name)
    if pattern.search(text):
        return pattern.sub(lambda _match: block, text, count=1)
    return text.rstrip("\n") + f"\n\n## {title}\n\n{block}\n"


def ensure_placeholder_section(text: str, name: str, title: str, placeholder: str) -> str:
    """Adds the section only if this marker has never been written; an existing one (filled by another tool, e.g.
    `score_spot_check.py`) is left completely untouched - this function never overwrites it."""
    if f"<!-- AUTO:{name} -->" in text:
        return text
    return replace_or_append_section(text, name, title, placeholder)


# --- assembling one report -------------------------------------------------------------------------------------

def build_report(runs: list[dict], spans_by_case: dict, chunk_indexes: dict, pricing: dict) -> dict:
    all_pairs = []
    for run in runs:
        index = chunk_indexes.get(run["manifest"]["config"]["arm"])
        all_pairs.extend(score_run_pairs(run, spans_by_case, index))
    rows = [row for _, row in all_pairs]
    breakdown = scoring.breakdown(rows)
    full_records = [record for run in runs for record in run["records"] if run["manifest"]["config"]["mode"] == "full"]
    ok_records = [record for run in runs for record in run["records"] if record["status"] == "ok"]
    judgement_lines = [line for run in runs for line in run["judgement_lines"]]
    return {
        "pairs": all_pairs, "rows": rows, "breakdown": breakdown,
        "cost": scoring.cost_summary(full_records, judgement_lines, pricing),
        "latency": summarize_latency(ok_records),
        "judge_latency": scoring.summarize_judge_latency(judgement_lines),
        "gate_refused_answerable": gate_refused_answerable(runs),
    }


def render_sections(runs: list[dict], report: dict) -> dict[str, str]:
    caption = base_caption(runs, report["rows"])
    overall = report["breakdown"]["overall"]
    bodies = {
        "retrieval": retrieval_table(overall["retrieval"]),
        "answer": answer_table(overall["answer"]),
        "refusal": refusal_table(overall["answer"]),
        "citation": citation_table(overall["citation"]),
        "latency": latency_table(report["latency"], report["judge_latency"]),
        "cost": cost_table(report["cost"]),
        "per_language": per_language_table(report["breakdown"]),
        "parallel": parallel_table(report["breakdown"]),
        "per_case": per_case_table(report["pairs"]),
    }
    gate = report["gate_refused_answerable"]
    gate_note = f"\n\n- answerable cases refused by the retrieval gate: " + (", ".join(gate) or "(none)") + "."
    return {name: caption + "\n\n" + body + (gate_note if name in ("retrieval", "answer") else "")
           for name, body in bodies.items()}


def write_report(out_path: Path, runs: list[dict], report: dict) -> None:
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else "# EPIC-05 evaluation report (generated)\n"
    sections = render_sections(runs, report)
    for name in SECTION_ORDER:
        text = replace_or_append_section(text, name, SECTION_TITLES[name], sections[name])
    text = ensure_placeholder_section(text, JUDGE_AGREEMENT_NAME, JUDGE_AGREEMENT_TITLE, JUDGE_AGREEMENT_PLACEHOLDER)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")


def write_summary_json(path: Path, runs: list[dict], report: dict) -> None:
    per_case = []
    for record, row in sorted(report["pairs"], key=lambda pair: (pair[0]["case_id"], pair[0]["arm"], pair[0]["mode"])):
        answer, citation = row.get("answer") or {}, row.get("citation") or {}
        per_case.append({
            "case_id": record["case_id"], "arm": record["arm"], "mode": record["mode"], "split": row["split"],
            "language": record["language"], "status": record["status"], "result": answer.get("result"),
            "points_covered": answer.get("points_covered"), "citation_auto_class": citation.get("auto_class"),
            "citation_judge_class": citation.get("judge_class"), "gate_fired": record.get("gate_fired"),
            "latency_total_ms": record["latency_ms"].get("total"), "spans_unavailable": row["spans_unavailable"],
        })
    summary = {
        "run_ids": [run["run_id"] for run in runs],
        "runs": [{"run_id": run["run_id"], "arm": run["manifest"]["config"]["arm"],
                 "mode": run["manifest"]["config"]["mode"], "split": run["split"], "records": len(run["records"])}
                for run in runs],
        "gate_refused_answerable": report["gate_refused_answerable"],
        "breakdown": report["breakdown"],
        "latency": report["latency"],
        "judge_latency": report["judge_latency"],
        "cost": report["cost"],
        "per_case": per_case,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def expected_source_field(record: dict) -> str:
    return "; ".join(f"{source['source_id']} {source['heading_path']}" for source in record["expected_sources"])


def citations_field(record: dict) -> str:
    return "; ".join(f"[{citation['marker']}] {citation['source_id']} {citation['heading_path']}"
                     for citation in record["citations"])


def csv_rows(pairs: list[tuple]) -> list[dict]:
    rows = []
    for record, row in pairs:
        answer = row.get("answer") or {}
        rows.append({
            "question": record["question"], "expected_answer": record["expected_answer"] or "",
            "expected_source": expected_source_field(record), "generated_answer": record["answer"] or "",
            "result": answer.get("result") or "", "case_id": record["case_id"], "arm": record["arm"],
            "language": record["language"], "citations": citations_field(record),
            "latency_total_ms": record["latency_ms"].get("total"),
        })
    return rows


def write_csv(path: Path, pairs: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in csv_rows(pairs):
            writer.writerow(row)


# --- CLI ----------------------------------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog=__doc__.split("\n\n", 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", nargs="+", required=True, metavar="RUN_ID", help="one or more run ids under data/evaluation/results/")
    parser.add_argument("--out", type=Path, default=None, help=f"report path (default {DEFAULT_OUT})")
    return parser.parse_args(argv)


def _resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def main(argv=None, *, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        runs = load_runs(args.runs, root=root)
        spans_by_case = load_spans_by_case(root=root)
        chunk_indexes = build_chunk_indexes(runs)
        pricing = load_pricing(root=root)
        report = build_report(runs, spans_by_case, chunk_indexes, pricing)

        report_path = _resolve(args.out or DEFAULT_OUT, root)
        write_report(report_path, runs, report)
        summary_path = root / "data" / "evaluation" / "results" / f"summary-{'-'.join(args.runs)}.json"
        write_summary_json(summary_path, runs, report)
        csv_paths = []
        for run in runs:
            index = chunk_indexes.get(run["manifest"]["config"]["arm"])
            pairs = score_run_pairs(run, spans_by_case, index)
            csv_path = root / "data" / "evaluation" / "results" / f"eval-table-{run['run_id']}.csv"
            write_csv(csv_path, pairs)
            csv_paths.append(csv_path)

        print(f"report: {report_path}", file=out)
        print(f"summary: {summary_path}", file=out)
        for csv_path in csv_paths:
            print(f"csv: {csv_path}", file=out)
        return EXIT_OK
    except EvaluationError as error:
        print(f"ABORTED: {error}", file=err)
        return EXIT_ABORTED


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
