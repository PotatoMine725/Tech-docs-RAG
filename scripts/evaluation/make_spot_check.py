"""EVAL-003c: draw a stratified sample of judge-checked records for the owner's spot-check (evaluation-spec.md §
Answer and citation scoring, "Limitation": the judge is the same model as the answer model).

    python scripts/evaluation/make_spot_check.py --run RUN_ID [--fraction 0.2] [--seed 42] [--out PATH]

Only records the LLM judge actually verdicted (`judge_status == "ok"`, i.e. an answer check or a refusal check ran
and parsed) are eligible: a bare gate refusal or a false refusal never called the judge, so there is no judge verdict
to spot-check. Eligible records are stratified by `(result, language)` (the six-way result label from
`metrics/mapping.py`, crossed with `en`/`vi`); every non-empty stratum contributes at least one record, and the
overall sample size is `round(fraction * n)` rounded up to cover every stratum. Sampling within a stratum is a seeded
shuffle (`random.Random(seed)`): the same run, fraction and seed always draw the same cases.

Writes `docs/reviews/evaluation/judge-spot-check-<run>.md`: one section per sampled case with the question, the
expected answer, the generated answer, the cited excerpts, the judge's own result and reason, and two blank fields
for the owner to fill by hand: `human_result` and `human_note`. `scripts/evaluation/score_spot_check.py` reads the
filled sheet back.

Zero Gemini requests: offline, reads only what `run_eval.py` and `judge_run.py` already wrote to disk.
"""
import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation.judge import OK, cited_passages  # noqa: E402
from knowledge_assistant.core.exceptions import EvaluationError  # noqa: E402
from scripts.evaluation.validate_questions import collapse_whitespace  # noqa: E402

from scripts.evaluation.eval_report_data import (  # noqa: E402
    build_chunk_indexes,
    judgements_and_prompt_version,
    load_run,
    load_spans_by_case,
    score_run_pairs,
)

DEFAULT_OUT_TEMPLATE = "docs/reviews/evaluation/judge-spot-check-{run_id}.md"
EXIT_OK, EXIT_ABORTED = 0, 3


# --- sampling (pure) ------------------------------------------------------------------------------------------

def judge_checked_pairs(pairs: list[tuple[dict, dict]]) -> list[tuple[dict, dict]]:
    """Records with an ok judge verdict: an answer check or a refusal check that parsed (`judge_status == "ok"`)."""
    return [(record, row) for record, row in pairs if row.get("answer") and row["answer"]["judge_status"] == OK]


def stratum_key(record: dict, row: dict) -> tuple[str, str]:
    return row["answer"]["result"], record["language"]


def stratify(pairs: list[tuple[dict, dict]]) -> dict[tuple[str, str], list[tuple[dict, dict]]]:
    strata = defaultdict(list)
    for record, row in pairs:
        strata[stratum_key(record, row)].append((record, row))
    return dict(strata)


def sample_stratified(pairs: list[tuple[dict, dict]], fraction: float, seed: int) -> list[tuple[dict, dict]]:
    """At least one record per non-empty stratum, then round-robin (sorted stratum order) up to
    `max(strata, round(fraction * n))`, capped at each stratum's size. The pick within a stratum is a seeded shuffle,
    so the same (run, fraction, seed) always draws the same cases."""
    strata = {key: sorted(items, key=lambda pair: (pair[0]["case_id"], pair[0]["arm"])) for key, items in stratify(pairs).items()}
    if not strata:
        return []
    total = sum(len(items) for items in strata.values())
    keys = sorted(strata)
    target = min(total, max(len(keys), round(total * fraction)))
    alloc = {key: 1 for key in keys}
    index = 0
    while sum(alloc.values()) < target:
        key = keys[index % len(keys)]
        if alloc[key] < len(strata[key]):
            alloc[key] += 1
        index += 1
        if index > 1000 * len(keys):  # every stratum exhausted (target already capped at `total`, so unreachable)
            break
    rng = random.Random(seed)
    selected = []
    for key in keys:
        items = list(strata[key])
        rng.shuffle(items)
        selected.extend(items[:alloc[key]])
    return selected


# --- rendering (pure) ------------------------------------------------------------------------------------------

def _clean(text: str | None) -> str:
    return collapse_whitespace(text) if text else "(none)"


def cited_excerpts(record: dict) -> list[str]:
    return [f"[{marker}] #{chunk['source_id']} {chunk['heading_path']} — {_clean(chunk['display_text'])}"
           for marker, chunk in cited_passages(record)]


def judgement_reason(record: dict, row: dict, judgements: dict, prompt_version: str | None) -> str:
    from knowledge_assistant.application.evaluation.scoring import find_judgement
    judgement = find_judgement(record, judgements, prompt_version)
    return _clean(judgement["verdict"]["reason"]) if judgement else "(no judgement found)"


def render_case(record: dict, row: dict, judgements: dict, prompt_version: str | None) -> str:
    excerpts = cited_excerpts(record)
    excerpt_lines = "\n".join(f"  - {excerpt}" for excerpt in excerpts) if excerpts else "  - (none)"
    lines = [
        f"## {record['case_id']} (arm {record['arm']}, {record['language']})",
        "",
        f"- **Question:** {_clean(record['question'])}",
        f"- **Expected answer:** {_clean(record['expected_answer'])}",
        f"- **Generated answer:** {_clean(record['answer'])}",
        "- **Cited excerpts:**",
        excerpt_lines,
        f"- **Judge result:** {row['answer']['result']}",
        f"- **Judge reason:** {judgement_reason(record, row, judgements, prompt_version)}",
        "- **human_result:** ",
        "- **human_note:** ",
    ]
    return "\n".join(lines)


# --- CLI ---------------------------------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID")
    parser.add_argument("--fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not 0 < args.fraction <= 1:
        parser.error("--fraction must be in (0, 1]")
    return args


def build_sheet(run_id: str, fraction: float, seed: int, root: Path) -> str:
    run = load_run(run_id, root=root)
    spans_by_case = load_spans_by_case(root=root)
    chunk_indexes = build_chunk_indexes([run])
    index = chunk_indexes.get(run["manifest"]["config"]["arm"])
    pairs = score_run_pairs(run, spans_by_case, index)
    eligible = judge_checked_pairs(pairs)
    sample = sample_stratified(eligible, fraction, seed)
    judgements, prompt_version = judgements_and_prompt_version(run["judgement_lines"])

    header = [
        f"# Judge spot-check — {run_id}",
        f"<!-- run_id: {run_id} -->",
        "",
        f"Stratified sample of judge-checked records (result x language), fraction {fraction}, seed {seed}, out of "
        f"{len(eligible)} eligible (judge-checked) record(s). {len(sample)} case(s) sampled. Fill `human_result` "
        "(one of the `result` labels: `correct`, `partially_correct`, `incorrect`, `correct_refusal`, "
        "`hallucination`) and `human_note` for every case below, then run "
        "`scripts/evaluation/score_spot_check.py <this file>`.",
        "",
    ]
    if not sample:
        header.append("*(No judge-checked records were available to sample.)*")
        return "\n".join(header) + "\n"
    ordered = sorted(sample, key=lambda pair: (pair[0]["case_id"], pair[0]["arm"]))
    blocks = [render_case(record, row, judgements, prompt_version) for record, row in ordered]
    return "\n".join(header) + "\n" + "\n\n---\n\n".join(blocks) + "\n"


def main(argv=None, *, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        text = build_sheet(args.run_id, args.fraction, args.seed, root)
        out_path = args.out if args.out and args.out.is_absolute() else root / (args.out or Path(
            DEFAULT_OUT_TEMPLATE.format(run_id=args.run_id)))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="\n")
        print(f"spot-check sheet: {out_path}", file=out)
        return EXIT_OK
    except EvaluationError as error:
        print(f"ABORTED: {error}", file=err)
        return EXIT_ABORTED


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
