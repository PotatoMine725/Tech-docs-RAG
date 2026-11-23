"""Compare the retrieval part of recorded runs (e.g. the Gemini runs and the local-embedder runs), side by side.

    python scripts/evaluation/compare_retrieval_runs.py --runs RUN_ID [RUN_ID ...]

Every number comes from the run folders under data/evaluation/results/ through the EVAL-003b scoring code
(`eval_report_data.score_runs` / `scoring.summarize_retrieval`); nothing is typed in. Prints Markdown:
- one summary row per run: cases, answerable, expected-source hit@1 / @5 (the case's expected `source_id`s, any
  slot), span metrics where `expected-spans-v1.json` covers the split (eval only), top-1 score range of answerable
  and unanswerable cases, and how often the gate fired on each;
- a per-case top-1 table (one column per run).
Full-mode runs are read for their retrieval fields only.
"""
import argparse
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from scripts.evaluation.eval_report_data import (  # noqa: E402
    build_chunk_indexes,
    load_runs,
    load_spans_by_case,
    score_runs,
)

SPAN_KEYS = ("evidence_hit@1", "evidence_hit@5", "mrr@5")


def source_hit(record: dict, k: int) -> bool:
    expected = {s["source_id"] for s in record["expected_sources"]} | \
        {s["source_id"] for s in record.get("acceptable_alternate_sources") or []}
    return any(chunk["source_id"] in expected for chunk in record["retrieved"][:k])


def _range(values: list[float]) -> str:
    return f"{min(values):.4f}–{max(values):.4f} (median {statistics.median(values):.4f})" if values else "–"


def _rate(hits: int, n: int) -> str:
    return f"{hits}/{n} ({hits / n:.3f})" if n else "–"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", nargs="+", required=True)
    args = parser.parse_args(argv)

    runs = load_runs(args.runs)
    spans = load_spans_by_case()
    rows = score_runs(runs, spans, build_chunk_indexes(runs))

    print("| run | embedding model | threshold | cases | answerable | source hit@1 | source hit@5 | "
          + " | ".join(SPAN_KEYS) + " | answerable top-1 | unanswerable top-1 | gate fired: answerable | "
          "gate fired: unanswerable |")
    print("|" + "---|" * (11 + len(SPAN_KEYS)))
    for run in runs:
        config = run["manifest"]["config"]
        ok = [r for r in run["records"] if r["status"] == "ok"]
        answerable = [r for r in ok if r["answerable"]]
        unanswerable = [r for r in ok if not r["answerable"]]
        summary = scoring.summarize_retrieval([row for row in rows if row["run_id"] == run["run_id"]
                                               and row["status"] == "ok"])
        span_cells = []
        for key in SPAN_KEYS:
            value = summary.get(key)
            span_cells.append(f"{value['mean']:.3f} (n={value['n']})" if value and value.get("n") else "–")
        print(f"| {run['run_id']} | {config['embedding_model']}@{config['embedding_dim']} | {config['threshold']} "
              f"| {len(ok)} | {len(answerable)} "
              f"| {_rate(sum(source_hit(r, 1) for r in answerable), len(answerable))} "
              f"| {_rate(sum(source_hit(r, 5) for r in answerable), len(answerable))} | " + " | ".join(span_cells)
              + f" | {_range([r['top1_score'] for r in answerable])} | {_range([r['top1_score'] for r in unanswerable])}"
              f" | {_rate(sum(bool(r['gate_fired']) for r in answerable), len(answerable))}"
              f" | {_rate(sum(bool(r['gate_fired']) for r in unanswerable), len(unanswerable))} |")

    print()
    cases = sorted({r["case_id"] for run in runs for r in run["records"]})
    by_run = {run["run_id"]: {r["case_id"]: r for r in run["records"] if r["status"] == "ok"} for run in runs}
    print("| case | language | answerable | " + " | ".join(f"top-1 {run_id}" for run_id in args.runs) + " |")
    print("|---|---|---|" + "---:|" * len(args.runs))
    for case in cases:
        first = next(by_run[run_id][case] for run_id in args.runs if case in by_run[run_id])
        cells = []
        for run_id in args.runs:
            record = by_run[run_id].get(case)
            cells.append("–" if record is None else
                         f"{record['top1_score']:.4f}{'' if source_hit(record, 1) or not record['answerable'] else ' ✗'}")
        print(f"| {case} | {first['language']} | {'yes' if first['answerable'] else 'no'} | " + " | ".join(cells) + " |")
    print("\n✗ = top-1 chunk is not from an expected (or acceptable alternate) source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
