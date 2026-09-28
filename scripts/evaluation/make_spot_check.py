"""EVAL-003c: draw a stratified sample of judge-checked records for the owner's spot-check (evaluation-spec.md §
Answer and citation scoring, "Limitation": the judge is the same model as the answer model).

    python scripts/evaluation/make_spot_check.py --run RUN_ID [--fraction 0.2] [--seed 42] [--out PATH] [--force]

Only records the LLM judge actually verdicted (`judge_status == "ok"`, i.e. an answer check or a refusal check ran
and parsed) are eligible: a bare gate refusal or a false refusal never called the judge, so there is no judge verdict
to spot-check. Eligible records are stratified by `(result, language)` (the six-way result label from
`metrics/mapping.py`, crossed with `en`/`vi`); every non-empty stratum contributes at least one record, and the
overall sample size is `round(fraction * n)` rounded up to cover every stratum. Sampling within a stratum is a seeded
shuffle (`random.Random(seed)`): the same run, fraction and seed always draw the same cases.

Writes two files (VERIFY EVAL-003c check 5 - the format `score_spot_check.py` reads and EVAL-004a's owner sheet
already used): `validation/evaluation/judge-spot-check-<run>.md`, one **blind** section per sampled case (no case id,
arm or judge label - the question, ground truth, generated answer and cited passages in full, and an `**Owner
verdict**` table of blank per-point grades for the owner to fill by hand), and
`validation/evaluation/judge-spot-check-<run>-judge.md`, the key (`## Sxx` -> case id, arm, run id, and the judge's
own verdict/label) the owner opens only after grading. Refuses to overwrite either file unless `--force` is given, so
a re-run can never clobber the owner's already-graded sheet.

Zero Gemini requests: offline, reads only what `run_eval.py` and `judge_run.py` already wrote to disk.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation.judge import ANSWER_CHECK, OK, cited_passages  # noqa: E402
from knowledge_assistant.core.exceptions import EvaluationError  # noqa: E402

from scripts.evaluation.eval_report_data import (  # noqa: E402
    build_chunk_indexes,
    judgements_and_prompt_version,
    load_run,
    load_spans_by_case,
    score_run_pairs,
)

DEFAULT_OUT_TEMPLATE = "validation/evaluation/judge-spot-check-{run_id}.md"
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


# --- rendering (pure): the blind sheet (VERIFY EVAL-003c check 5 - the format EVAL-004a's owner sheet used) -----

def quote_block(text: str | None) -> str:
    return "\n".join("> " + line if line.strip() else ">" for line in (text or "").splitlines()) or "> (empty)"


def render_case(sid: str, record: dict, judgement: dict) -> str:
    """One blind `## Sxx (... check)` section: full ground truth and cited passages (needed to grade), but no case
    id, arm or judge verdict - only a per-point `**Owner verdict**` table with blank cells."""
    check = judgement["check"]
    lines = [f"## {sid} ({'answer check' if check == ANSWER_CHECK else 'refusal check'})", "",
            f"**Question** ({record['language']}):", "", quote_block(record["question"]), "",
            "**Ground truth**", "", f"- Expected answer: {record['expected_answer']}"]
    for point in record["answer_points"]:
        lines.append(f"- {point['id']} ({'required' if point['required'] else 'optional, context only'}): {point['text']}")
    lines.append(f"- Acceptable variations: {'; '.join(record['acceptable_variations']) or 'none'}")
    lines.append(f"- MUST-NOT-CLAIM: {'; '.join(record['must_not_claim']) or 'none'}")
    lines.append(f"- Citation criteria: {'; '.join(record['citation_criteria']) or 'none'}")
    lines += ["", "**Answer**:", "", quote_block(record["answer"]), ""]
    if record["missing_information"]:
        lines += ["**Note about missing information**:", "", quote_block(record["missing_information"]), ""]
    passages = cited_passages(record)
    lines += [f"**Cited passages** ({len(passages)}):", ""]
    for marker, chunk in passages:
        lines += [f"[{marker}] #{chunk['source_id']} — {chunk['heading_path']}", "", quote_block(chunk["display_text"]), ""]
    lines += ["**Owner verdict**", ""]
    if check == ANSWER_CHECK:
        lines += ["| Item | Owner | Note |", "|---|---|---|"]
        lines += [f"| {point['id']} covered |  |  |" for point in record["answer_points"] if point["required"]]
        lines += ["| contradicts ground truth |  |  |", "| unsupported claims |  |  |"]
        lines += [f"| citation [{marker}] supports its claim |  |  |" for marker, _ in passages]
    else:
        lines += ["| Item | Owner | Note |", "|---|---|---|", "| presents_related_as_answer |  |  |"]
    lines += ["| agree with the judge? (fill after opening the key) |  |  |"]
    return "\n".join(lines)


def render_key_entry(sid: str, run_id: str, record: dict, judgement: dict, label: str) -> str:
    return "\n".join([f"## {sid}", "", f"- Case: `{record['case_id']}`, arm {record['arm']}, run `{run_id}`",
                      f"- Check: {judgement['check']}; judge model `{judgement['judge_model']}`; label: **{label}**", "",
                      "```json", json.dumps(judgement["verdict"], ensure_ascii=False, indent=1), "```"])


# --- CLI ---------------------------------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, dest="run_id", metavar="RUN_ID")
    parser.add_argument("--fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=None, help="blind sheet path (the key is the same name + '-judge')")
    parser.add_argument("--force", action="store_true", help="overwrite an existing sheet/key instead of refusing")
    args = parser.parse_args(argv)
    if not 0 < args.fraction <= 1:
        parser.error("--fraction must be in (0, 1]")
    return args


PREAMBLE = [
    "Grade each item yourself **before** opening the key file. That file holds the judge's verdicts and the S-id "
    "-> case / arm mapping. This file shows no label, no judge verdict and no arm.", "",
    "Grade with the judge's own rules (`config/prompts/judge_v1.md`), using only the ground truth and the cited "
    "passages shown, not your own knowledge:",
    "- **Answer check** (answerable question). Per required point: `yes` / `partial` / `no`. Contradicts ground "
    "truth or states a MUST-NOT-CLAIM item: `true` / `false`. Unsupported claims: quote them, or write `none`. Per "
    "citation marker: does the passage support the claim it is attached to: `yes` / `partial` / `no`.",
    "- **Refusal check** (question the documents do not answer). `presents_related_as_answer` is `true` if the "
    "response presents related content, or an inferred technique, as the documents' answer, makes a substantive "
    "answering claim, or never says the topic isn't covered; otherwise `false`.",
]


def build_sheets(run_id: str, fraction: float, seed: int, root: Path) -> tuple[str, str]:
    """(blind sheet text, key text) - `score_spot_check.py` reads both back; the owner's sheet is never re-derived
    from it (a re-run must not overwrite already-graded work - see `main`'s `--force` guard)."""
    from knowledge_assistant.application.evaluation.scoring import find_judgement

    run = load_run(run_id, root=root)
    spans_by_case = load_spans_by_case(root=root)
    chunk_indexes = build_chunk_indexes([run])
    index = chunk_indexes.get(run["manifest"]["config"]["arm"])
    pairs = score_run_pairs(run, spans_by_case, index)
    eligible = judge_checked_pairs(pairs)
    sample = sample_stratified(eligible, fraction, seed)
    judgements, prompt_version = judgements_and_prompt_version(run["judgement_lines"])

    header = [
        "# Judge spot-check: owner grading sheet (blind)", "",
        f"Run `{run_id}`. <!-- run_id: {run_id} -->", "",
    ] + PREAMBLE + [
        "",
        f"Stratified sample of judge-checked records (result x language), fraction {fraction}, seed {seed}, out of "
        f"{len(eligible)} eligible (judge-checked) record(s). {len(sample)} case(s) sampled. Owner columns are "
        "empty on purpose.", "",
    ]
    key_header = ["# Judge spot-check: the judge's verdicts (key)", "",
                 f"Run `{run_id}`. Open only after grading the blind sheet. One entry per S-id: the record it came "
                 f"from and the judge's verdict as written in `judgements.jsonl` (prompt `{prompt_version}`). The "
                 "label is the §3 mapping of that verdict.", ""]
    if not sample:
        header.append("*(No judge-checked records were available to sample.)*")
        return "\n".join(header) + "\n", "\n".join(key_header) + "\n"

    ordered = sorted(sample, key=lambda pair: (pair[0]["case_id"], pair[0]["arm"]))
    blind_blocks, key_blocks = [], []
    for i, (record, row) in enumerate(ordered, 1):
        sid = f"S{i:02d}"
        judgement = find_judgement(record, judgements, prompt_version)
        blind_blocks.append(render_case(sid, record, judgement))
        key_blocks.append(render_key_entry(sid, run_id, record, judgement, row["answer"]["result"]))
    blind = "\n".join(header) + "\n" + "\n\n---\n\n".join(blind_blocks) + "\n"
    key = "\n".join(key_header) + "\n" + "\n\n---\n\n".join(key_blocks) + "\n"
    return blind, key


def _out_paths(args, root: Path) -> tuple[Path, Path]:
    out_path = args.out if args.out and args.out.is_absolute() else root / (args.out or Path(
        DEFAULT_OUT_TEMPLATE.format(run_id=args.run_id)))
    key_path = out_path.with_name(out_path.stem + "-judge" + out_path.suffix)
    return out_path, key_path


def main(argv=None, *, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        out_path, key_path = _out_paths(args, root)
        existing = [str(path) for path in (out_path, key_path) if path.exists()]
        if existing and not args.force:
            raise EvaluationError(f"refusing to overwrite existing file(s) without --force: {', '.join(existing)}")
        blind, key = build_sheets(args.run_id, args.fraction, args.seed, root)
        for path, text in ((out_path, blind), (key_path, key)):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
        print(f"spot-check sheet: {out_path}", file=out)
        print(f"spot-check key: {key_path}", file=out)
        return EXIT_OK
    except EvaluationError as error:
        print(f"ABORTED: {error}", file=err)
        return EXIT_ABORTED


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
