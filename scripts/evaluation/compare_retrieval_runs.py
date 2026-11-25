"""Compare the retrieval part of recorded runs (e.g. the Gemini runs and the local-embedder runs), side by side.

    python scripts/evaluation/compare_retrieval_runs.py --runs RUN_ID [RUN_ID ...]

Every number comes from the run folders under data/evaluation/results/ through the EVAL-003b scoring code
(`eval_report_data.score_runs` / `scoring.summarize_retrieval`); nothing is typed in. Prints Markdown:
- one summary row per run: cases, answerable, expected-source hit@1 / @5 (the case's expected `source_id`s, any
  slot), span metrics where `expected-spans-v1.json` covers the split (eval only), top-1 score range of answerable
  and unanswerable cases, and how often the gate fired on each;
- one row per run and question language (en, vi): the same hit rates over that language's answerable cases, with n;
- a per-case top-1 table (one column per run), unless --no-cases.
`retrieval` is the run's RETRIEVAL_MODE (ADR-0007; runs recorded before it have none and were dense). `top1_score` is the
gate input, the dense top-1 cosine, in every mode, so its ranges and the gate columns do not depend on the mode; an
`errors` column counts cases without an ok record (e.g. a sparse run whose question matched no keyword).
Full-mode runs are read for their retrieval fields only. Duplicates resolve through the arms' full chunk files.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from knowledge_assistant.config import get_chunks_dir  # noqa: E402
from scripts.evaluation.eval_report_data import (  # noqa: E402
    load_runs,
    load_spans_by_case,
    score_runs,
)

SPAN_KEYS = ("source_hit@1", "section_hit@1", "evidence_hit@1", "source_hit@5", "section_hit@5", "evidence_hit@5", "mrr")


def full_chunk_indexes(runs: list[dict]) -> dict[str, dict]:
    """{arm: chunk_index} from the arm's whole chunk file, so every `duplicate_chunk_ids` entry resolves (the
    retrieved-chunks-only index of `eval_report_data.build_chunk_indexes` cannot resolve a duplicate no run retrieved)."""
    indexes = {}
    for arm in {run["manifest"]["config"]["arm"] for run in runs}:
        path = get_chunks_dir() / f"arm-{arm.lower()}.jsonl"
        with path.open(encoding="utf-8") as lines:
            indexes[arm] = chunk_index([json.loads(line) for line in lines if line.strip()])
    return indexes


def source_hit(record: dict, k: int) -> bool:
    expected = {s["source_id"] for s in record["expected_sources"]} | \
        {s["source_id"] for s in record.get("acceptable_alternate_sources") or []}
    return any(chunk["source_id"] in expected for chunk in record["retrieved"][:k])


def _range(values: list[float]) -> str:
    return f"{min(values):.4f}–{max(values):.4f} (median {statistics.median(values):.4f})" if values else "–"


def _rate(hits: int, n: int) -> str:
    return f"{hits}/{n} ({hits / n:.3f})" if n else "–"


def retrieval_mode(run: dict) -> str:
    return run["manifest"]["config"].get("retrieval_mode", "dense")


def _span_cells(rows: list[dict]) -> list[str]:
    summary = scoring.summarize_retrieval(rows) if rows else {}
    cells = []
    for key in SPAN_KEYS:
        value = summary.get(key)
        cells.append(f"{value['value']:.3f}" if value and value.get("value") is not None else "–")
    return cells


def print_language_table(runs: list[dict], rows: list[dict]) -> None:
    """One row per run x language: hit rates over that language's answerable ok cases (span metrics where covered)."""
    print("| run | retrieval | language | answerable n | expected source in top-1 | expected source in top-5 | "
          + " | ".join(SPAN_KEYS) + " | gate fired: answerable |")
    print("|" + "---|" * (7 + len(SPAN_KEYS)))
    for run in runs:
        ok = [r for r in run["records"] if r["status"] == "ok"]
        for language in sorted({r["language"] for r in ok}):
            answerable = [r for r in ok if r["answerable"] and r["language"] == language]
            lang_rows = [row for row in rows if row["run_id"] == run["run_id"] and row["status"] == "ok"
                         and row["language"] == language and row["answerable"]]
            print(f"| {run['run_id']} | {retrieval_mode(run)} | {language} | {len(answerable)} "
                  f"| {_rate(sum(source_hit(r, 1) for r in answerable), len(answerable))} "
                  f"| {_rate(sum(source_hit(r, 5) for r in answerable), len(answerable))} | "
                  + " | ".join(_span_cells(lang_rows))
                  + f" | {_rate(sum(bool(r['gate_fired']) for r in answerable), len(answerable))} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--no-cases", action="store_true", help="skip the per-case top-1 table")
    args = parser.parse_args(argv)

    runs = load_runs(args.runs)
    spans = load_spans_by_case()
    rows = score_runs(runs, spans, full_chunk_indexes(runs))

    print("| run | retrieval | embedding model | threshold | cases | errors | answerable | expected source in top-1 | "
          "expected source in top-5 | " + " | ".join(SPAN_KEYS) + " | answerable top-1 | unanswerable top-1 | "
          "gate fired: answerable | gate fired: unanswerable |")
    print("|" + "---|" * (13 + len(SPAN_KEYS)))
    for run in runs:
        config = run["manifest"]["config"]
        ok = [r for r in run["records"] if r["status"] == "ok"]
        answerable = [r for r in ok if r["answerable"]]
        unanswerable = [r for r in ok if not r["answerable"]]
        latest = {r["case_id"]: r for r in run["records"]}  # records are append-only; the last line of a case wins
        errors = sum(1 for r in latest.values() if r["status"] != "ok")
        span_cells = _span_cells([row for row in rows if row["run_id"] == run["run_id"] and row["status"] == "ok"])
        print(f"| {run['run_id']} | {retrieval_mode(run)} | {config['embedding_model']}@{config['embedding_dim']} "
              f"| {config['threshold']} | {len(ok)} | {errors} | {len(answerable)} "
              f"| {_rate(sum(source_hit(r, 1) for r in answerable), len(answerable))} "
              f"| {_rate(sum(source_hit(r, 5) for r in answerable), len(answerable))} | " + " | ".join(span_cells)
              + f" | {_range([r['top1_score'] for r in answerable])} | {_range([r['top1_score'] for r in unanswerable])}"
              f" | {_rate(sum(bool(r['gate_fired']) for r in answerable), len(answerable))}"
              f" | {_rate(sum(bool(r['gate_fired']) for r in unanswerable), len(unanswerable))} |")

    print()
    print_language_table(runs, rows)
    if args.no_cases:
        return 0

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
