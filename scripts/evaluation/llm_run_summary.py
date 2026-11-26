"""Local LLM comparison: the non-judge metrics of full-mode runs (docs/plans/local-llm-preregistration.md §4).

    python scripts/evaluation/llm_run_summary.py --runs RUN_ID [RUN_ID ...] [--reference RUN_ID] [--known-differences ID,ID]

Reads `data/evaluation/results/<run_id>/run.json` and `records.jsonl` (latest line per case). Decides nothing: it
prints one Markdown row per run with
- `model`, `prompt`: from run.json;
- `ok` / `errors`: cases with an ok record and cases without one;
- `answered`, `llm_refused`, `gate`: answered by the LLM, refused by the LLM (sentinel / insufficient), stopped by the
  retrieval gate;
- `false_refusal_gate` / `false_refusal_llm` (plan amendment A2): answerable cases stopped by the gate, over all
  answerable ok cases; answerable cases the LLM refused, over answerable cases that reached the LLM (the <= 10% rule);
- `missing_marker`: answered cases with no valid citation, over answered (go/no-go: at most 10%);
- `lang_match`: LLM-written texts (answer, or the refusal note) whose detected language equals the question's, over
  those cases. Detection is the app's own rule (any Vietnamese diacritic = vi), so an English answer quoting a
  Vietnamese word counts as vi: check the mismatched case ids it lists;
- `ttft_ms` median / p90 and `gen_ms` median (the `generate` stage, wall time) over LLM calls; ttft is null for Gemini;
- `same_retrieval`: with --reference, whether every shared case retrieved the same chunk ids in the same order as in
  the reference run (the LLM must be the only variable, plan §4.2). A mismatch lists the case ids and the exit code is 1.
  `--known-differences` (owner-accepted deviations, logged in the report): a listed case is accepted only if the gate
  fired on it in both the run and the reference (so no LLM saw it and it cannot enter a generation metric); it is
  shown as `yes*`. A listed case that reached an LLM in either run, or any unlisted difference, still exits 1.
Accuracy, false refusal and hallucination come from the judge (`judge_run.py`, `make_tables.py`), not from here.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.common.language import detect_language  # noqa: E402
from knowledge_assistant.application.evaluation.records import latest_records  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "data" / "evaluation" / "results"


def load_run(run_id: str, results_dir: Path = RESULTS_DIR) -> tuple[dict, list[dict]]:
    directory = results_dir / run_id
    config = json.loads((directory / "run.json").read_text(encoding="utf-8"))
    lines = (directory / "records.jsonl").read_text(encoding="utf-8").splitlines()
    records = list(latest_records([json.loads(line) for line in lines if line.strip()]).values())
    return config, records


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def summarize(config: dict, records: list[dict]) -> dict:
    ok = [r for r in records if r["status"] == "ok"]
    llm = [r for r in ok if r["llm_called"]]
    answered = [r for r in llm if not r["insufficient"]]
    refused = [r for r in llm if r["insufficient"]]
    missing = [r["case_id"] for r in answered if not r["citations"]]
    written = [(r, r["answer"] if not r["insufficient"] else (r["missing_information"] or "")) for r in llm]
    judged = [(r, text) for r, text in written if text.strip()]
    mismatched = [r["case_id"] for r, text in judged if detect_language(text) != r["language"]]
    ttft = [r["time_to_first_token_ms"] for r in llm if r.get("time_to_first_token_ms") is not None]
    gen = [r["latency_ms"]["generate"] for r in llm if r["latency_ms"].get("generate") is not None]
    answerable = [r for r in ok if r.get("answerable")]
    reached = [r for r in answerable if r["llm_called"]]
    gate_refused = [r["case_id"] for r in answerable if r["gate_fired"]]
    llm_refused = [r["case_id"] for r in reached if r["insufficient"]]
    run_config = config.get("config", config)
    return {
        "model": run_config.get("answer_model"),
        "prompt": run_config.get("prompt_version"),
        "ok": len(ok),
        "errors": len(records) - len(ok),
        "answered": len(answered),
        "llm_refused": len(refused),
        "gate": sum(1 for r in ok if r["gate_fired"]),
        "false_refusal_gate": len(gate_refused) / len(answerable) if answerable else None,
        "false_refusal_gate_cases": gate_refused,
        "false_refusal_llm": len(llm_refused) / len(reached) if reached else None,
        "false_refusal_llm_cases": llm_refused,
        "missing_marker": len(missing) / len(answered) if answered else None,
        "missing_marker_cases": missing,
        "lang_match": 1 - len(mismatched) / len(judged) if judged else None,
        "lang_mismatch_cases": mismatched,
        "ttft_median_ms": statistics.median(ttft) if ttft else None,
        "ttft_p90_ms": _percentile(ttft, 0.9),
        "gen_median_ms": statistics.median(gen) if gen else None,
    }


def accepted_differences(bad: list[str], known: set[str], records: list[dict], reference: list[dict]) -> tuple[list, list]:
    """(accepted, rejected): a known case is accepted only when the gate fired on it in both runs."""
    gated = lambda rows: {r["case_id"] for r in rows if r["status"] == "ok" and r["gate_fired"]}  # noqa: E731
    both = gated(records) & gated(reference)
    accepted = [case for case in bad if case in known and case in both]
    return accepted, [case for case in bad if case not in accepted]


def retrieval_mismatches(records: list[dict], reference: list[dict]) -> list[str]:
    """Case ids (present and ok in both) whose retrieved chunk ids differ in content or order."""
    ref = {r["case_id"]: [c["chunk_id"] for c in r["retrieved"]] for r in reference if r["status"] == "ok"}
    return [r["case_id"] for r in records
            if r["status"] == "ok" and r["case_id"] in ref and [c["chunk_id"] for c in r["retrieved"]] != ref[r["case_id"]]]


def _fmt(value, kind: str = "") -> str:
    if value is None:
        return "n/a"
    if kind == "pct":
        return f"{value:.1%}"
    if kind == "ms":
        return f"{value:,.0f}"
    return str(value)


def main(argv: list[str] | None = None, results_dir: Path = RESULTS_DIR) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", nargs="+", required=True)
    parser.add_argument("--reference", help="run whose retrieval every other run must match")
    parser.add_argument("--known-differences", default="",
                        help="comma-separated case ids whose retrieval difference the owner accepted (gate-only)")
    args = parser.parse_args(argv)
    reference = load_run(args.reference, results_dir)[1] if args.reference else None
    print("| run | model | prompt | ok | errors | answered | llm_refused | gate | false_refusal gate | false_refusal llm | "
          "missing_marker | lang_match | "
          "ttft median ms | ttft p90 ms | gen median ms | same_retrieval |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    notes, exit_code = [], 0
    for run_id in args.runs:
        config, records = load_run(run_id, results_dir)
        s = summarize(config, records)
        same = "n/a"
        if reference is not None:
            known = {case.strip() for case in args.known_differences.split(",") if case.strip()}
            accepted, bad = accepted_differences(retrieval_mismatches(records, reference), known, records, reference)
            same = f"NO ({len(bad)})" if bad else ("yes*" if accepted else "yes")
            if bad:
                exit_code = 1
                notes.append(f"- {run_id}: retrieval differs from {args.reference} on {', '.join(bad)}")
            if accepted:
                notes.append(f"- {run_id}: accepted known difference (gate fired in both runs, no LLM saw it): "
                             f"{', '.join(accepted)}")
        print(f"| {run_id} | {s['model']} | {s['prompt']} | {s['ok']} | {s['errors']} | {s['answered']} | "
              f"{s['llm_refused']} | {s['gate']} | {_fmt(s['false_refusal_gate'], 'pct')} | "
              f"{_fmt(s['false_refusal_llm'], 'pct')} | {_fmt(s['missing_marker'], 'pct')} | {_fmt(s['lang_match'], 'pct')} | "
              f"{_fmt(s['ttft_median_ms'], 'ms')} | {_fmt(s['ttft_p90_ms'], 'ms')} | {_fmt(s['gen_median_ms'], 'ms')} | "
              f"{same} |")
        if s["false_refusal_llm_cases"]:
            notes.append(f"- {run_id}: answerable, refused by the LLM: {', '.join(s['false_refusal_llm_cases'])}")
        if s["false_refusal_gate_cases"]:
            notes.append(f"- {run_id}: answerable, stopped by the gate: {', '.join(s['false_refusal_gate_cases'])}")
        if s["missing_marker_cases"]:
            notes.append(f"- {run_id}: no valid marker in {', '.join(s['missing_marker_cases'])}")
        if s["lang_mismatch_cases"]:
            notes.append(f"- {run_id}: language mismatch in {', '.join(s['lang_mismatch_cases'])}")
    if notes:
        print("\n" + "\n".join(notes))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
