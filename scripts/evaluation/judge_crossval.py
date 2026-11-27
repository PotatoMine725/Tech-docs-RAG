"""Judge cross-validation on owner-reviewed items: re-judge them with another judge model into a SEPARATE file.

    python scripts/evaluation/judge_crossval.py run --items ITEMS.json [--estimate-only]
    python scripts/evaluation/judge_crossval.py compare --items ITEMS.json --model MODEL

ITEMS.json: a list of {"item": "S01", "run": RUN_ID, "case": CASE_ID, "owner": LABEL} (the owner's blind grades,
labels as in metrics/mapping.py). `run` re-judges exactly those (run, case) pairs with the judge model in
JUDGE_MODEL (e.g. JUDGE_MODEL=gemini-3.8-flash, key JUDGE_API_KEY): each run's run.json and records.jsonl are copied
to a staging folder, `judge_run.py` runs there unchanged with --cases, and the staging judgements are written next to
the run as `judgements.crossval-<model>.jsonl`. The run's own `judgements.jsonl` is never read, written or replaced,
so the tables keep their judge. A cross-validation file that already exists is resumed (its ok lines stay cached).
`compare` prints owner vs the run's judge (judgements.jsonl) vs the cross-validation judge, per item and in total.
Decides nothing: changing the judge or a threshold is the owner's call.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path("data") / "evaluation" / "results"
for _extra in (PROJECT_ROOT, PROJECT_ROOT / "src", PROJECT_ROOT / "scripts" / "evaluation"):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation import scoring  # noqa: E402
from knowledge_assistant.application.evaluation.judge import latest_judgements  # noqa: E402


def crossval_name(model: str) -> str:
    return f"judgements.crossval-{model}.jsonl"


def load_items(path: Path) -> list[dict]:
    items = json.loads(path.read_text(encoding="utf-8"))
    for item in items:
        if not {"item", "run", "case", "owner"} <= set(item):
            raise SystemExit(f"item without item/run/case/owner: {item}")
    return items


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def labels_from(records: list[dict], lines: list[dict]) -> dict:
    """{case_id: label} for the given records under the given judgement lines (None = unlabelled)."""
    versions = {line["judge_prompt_version"] for line in lines}
    if len(versions) > 1:
        raise SystemExit(f"several judge prompt versions {sorted(versions)}")
    version = versions.pop() if versions else ""
    judgements = latest_judgements(lines)
    return {r["case_id"]: scoring.answer_scores(r, scoring.find_judgement(r, judgements, version))["result"]
            for r in records}


def latest(records: list[dict]) -> list[dict]:
    from knowledge_assistant.application.evaluation.records import latest_records
    return [record for record in latest_records(records).values() if record.get("status") == "ok"]


def run(items: list[dict], root: Path, model: str, estimate_only: bool, judge_main=None) -> int:
    if judge_main is None:
        import judge_run
        judge_main = judge_run.main
    by_run: dict[str, list[str]] = {}
    for item in items:
        by_run.setdefault(item["run"], []).append(item["case"])
    calls, worst = 0, 0
    with tempfile.TemporaryDirectory(prefix="crossval-") as staging:
        staging = Path(staging)
        for run_id, cases in sorted(by_run.items()):
            source, target = root / RESULTS / run_id, staging / RESULTS / run_id
            target.mkdir(parents=True)
            for name in ("run.json", "records.jsonl"):
                shutil.copyfile(source / name, target / name)
            existing = source / crossval_name(model)
            if existing.exists():  # resume: earlier ok cross-validation verdicts stay cached
                shutil.copyfile(existing, target / "judgements.jsonl")
            argv = ["--run-id", run_id, "--cases", ",".join(sorted(set(cases)))] + (["--estimate-only"] if estimate_only else [])
            code = judge_main(argv, root=staging)
            worst = max(worst, code)
            produced = target / "judgements.jsonl"
            if not estimate_only and produced.exists():
                shutil.copyfile(produced, existing)
            calls += len(set(cases))
    print(f"{len(items)} items in {len(by_run)} runs; up to {calls} judge calls with {model} (retries extra)")
    return worst


def compare(items: list[dict], root: Path, model: str) -> list[dict]:
    rows = []
    cache = {}
    for item in items:
        if item["run"] not in cache:
            directory = root / RESULTS / item["run"]
            records = latest(_read_jsonl(directory / "records.jsonl"))
            cache[item["run"]] = (labels_from(records, _read_jsonl(directory / "judgements.jsonl")),
                                  labels_from(records, _read_jsonl(directory / crossval_name(model))))
        base, cross = cache[item["run"]]
        rows.append({**item, "judge": base.get(item["case"]), "crossval": cross.get(item["case"])})
    return rows


def summary(rows: list[dict]) -> Counter:
    counts = Counter()
    for row in rows:
        counts["items"] += 1
        counts["owner=judge"] += row["owner"] == row["judge"]
        counts["crossval labelled"] += row["crossval"] is not None
        counts["owner=crossval"] += row["crossval"] is not None and row["owner"] == row["crossval"]
        counts["judge=crossval"] += row["crossval"] is not None and row["judge"] == row["crossval"]
    return counts


def main(argv=None, root: Path = PROJECT_ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=("run", "compare"))
    parser.add_argument("--items", type=Path, required=True)
    parser.add_argument("--model", help="compare: the cross-validation judge model (run: JUDGE_MODEL)")
    parser.add_argument("--estimate-only", action="store_true")
    args = parser.parse_args(argv)
    items = load_items(args.items)
    if args.action == "run":
        model = os.environ.get("JUDGE_MODEL")
        if not model:
            raise SystemExit("set JUDGE_MODEL to the cross-validation judge (e.g. gemini-3.8-flash)")
        return run(items, root, model, args.estimate_only)
    if not args.model:
        parser.error("compare needs --model")
    rows = compare(items, root, args.model)
    print(f"| item | run | case | owner | judge | {args.model} |\n|---|---|---|---|---|---|")
    for row in rows:
        print(f"| {row['item']} | {row['run']} | {row['case']} | {row['owner']} | {row['judge']} | {row['crossval']} |")
    print("\n" + ", ".join(f"{k}: {v}" for k, v in summary(rows).items()))
    return 0


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())  # walks up from the working directory, so a worktree inside the repo finds its .env
    sys.exit(main())
