"""EVAL-003c: score the owner's blind judge spot-check sheet (owner review of `evaluation-spec.md` §
"Limitation": the judge is the same model as the answer model).

    python scripts/evaluation/score_spot_check.py SHEET_FILE KEY_FILE [--out PATH]

Reads a sheet written by `make_spot_check.py` (blind: one `## Sxx (answer|refusal check)` section per sampled case,
each with an `**Owner verdict**` table of blank per-point grades - no case id, arm or judge label) and its separate
key file (`## Sxx` -> case id, arm, run, the judge's own verdict and label). Never writes to either file.

Refuses to run - no output written - while any owner grade is still blank, or while the sheet and key disagree on
which S-ids exist, so a half-filled or mismatched pair can never silently produce a score.

The owner's label is not read off a typed field: it is derived the same way the judge's label was, by running the
owner's own per-point grades through `metrics.mapping.map_result` (the record's own answerable/insufficient/
citations feed the same function). This is the **rule-based** figure and the headline this script reports -
agreement, Cohen's kappa, the confusion matrix and the disagreements (with both sides' stated reasons). The sheet
also carries a holistic, self-reported "agree with the judge?" column; that is reported only as a secondary line,
since it ignores `map_result` and can disagree with the rule-based figure (VERIFY EVAL-003c check 5).

Writes the section into `--out` (default `docs/reports/epics/EPIC-05-evaluation.md`, matching `make_tables.py`)
between `<!-- AUTO:judge_agreement --> ... <!-- /AUTO:judge_agreement -->` markers - the same markers `make_tables.py`
seeds with a placeholder, now filled in. Text outside the markers is never touched.

Zero Gemini requests: offline, reads only the local sheet, key and run files already on disk.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation.judge import has_related_note  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.mapping import JudgeVerdict, map_result  # noqa: E402
from knowledge_assistant.core.exceptions import EvaluationError  # noqa: E402

from scripts.evaluation.eval_report_data import load_run  # noqa: E402
from scripts.evaluation.make_tables import (  # noqa: E402
    JUDGE_AGREEMENT_NAME,
    JUDGE_AGREEMENT_TITLE,
    DEFAULT_OUT,
    md_table,
    replace_or_append_section,
)

EXIT_OK, EXIT_ABORTED = 0, 3
HOLISTIC_ITEM = "agree with the judge? (fill after opening the key)"

CASE_HEADER = re.compile(r"^## (?P<sid>S\d+) \((?P<check>answer|refusal) check\)\s*$", re.MULTILINE)
POINT_ITEM = re.compile(r"^P(\d+) covered$")
KEY_HEADER = re.compile(
    r"^## (?P<sid>S\d+)\n\n- Case: `(?P<case_id>\S+)`, arm (?P<arm>\S+), run `(?P<run_id>\S+)`\n"
    r"- Check: (?P<check>\w+); judge model `(?P<model>[^`]+)`; label: \*\*(?P<label>\w+)\*\*", re.MULTILINE)
JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


class SpotCheckError(ValueError):
    """The sheet/key pair is missing data this script needs (a blank grade, an unparseable case, a mismatched
    S-id, a record this key no longer points to, ...)."""


# --- parsing the owner's blind sheet (never modifies it) -------------------------------------------------------

def parse_owner_sheet(text: str) -> dict[str, dict]:
    """{sid: {"check": "answer"|"refusal", "grades": {item: (value, note)}}}, one entry per `## Sxx (... check)`
    heading and its `**Owner verdict**` table."""
    chunks = re.split(r"(?m)^## ", text)
    cases = {}
    for chunk in chunks[1:]:  # chunks[0] is the file header/preamble before the first case
        chunk = "## " + chunk
        header = CASE_HEADER.match(chunk)
        if not header:
            raise SpotCheckError(f"cannot parse a case heading: {chunk.splitlines()[0]!r}")
        cases[header["sid"]] = {"check": header["check"], "grades": _owner_table(chunk, header["sid"])}
    if not cases:
        raise SpotCheckError("no `## Sxx (answer|refusal check)` sections found - not a make_spot_check.py sheet?")
    return cases


def _owner_table(chunk: str, sid: str) -> dict[str, tuple[str, str]]:
    marker = "**Owner verdict**"
    idx = chunk.find(marker)
    if idx == -1:
        raise SpotCheckError(f"{sid}: no **Owner verdict** table")
    rows = [line for line in chunk[idx:].splitlines() if line.strip().startswith("|")]
    grades = {}
    for line in rows[2:]:  # rows[0] is the header row, rows[1] the '---' separator
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        grades[cells[0]] = (cells[1], cells[2] if len(cells) > 2 else "")
    return grades


def check_filled(cases: dict[str, dict]) -> None:
    blank = [f"{sid}:{item}" for sid, case in sorted(cases.items()) for item, (value, _note) in case["grades"].items()
            if not value.strip()]
    if blank:
        raise SpotCheckError(f"blank owner grade(s): {', '.join(blank)} - fill every cell before scoring")


# --- parsing the key file ---------------------------------------------------------------------------------------

def parse_key(text: str) -> dict[str, dict]:
    """{sid: {case_id, arm, run_id, check, label, reason}} - one entry per `## Sxx` heading and its fenced json
    judge verdict (`reason` is that verdict's own `reason` field)."""
    matches = list(KEY_HEADER.finditer(text))
    if not matches:
        raise SpotCheckError("no `## Sxx` key entries found - not a make_spot_check.py key file?")
    entries = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = JSON_BLOCK.search(text, match.end(), end)
        if not block:
            raise SpotCheckError(f"{match['sid']}: no fenced json verdict block")
        verdict = json.loads(block.group(1))
        entries[match["sid"]] = {"case_id": match["case_id"], "arm": match["arm"], "run_id": match["run_id"],
                                 "check": match["check"], "label": match["label"], "reason": verdict.get("reason", "")}
    return entries


# --- the owner's rule-based label: the same map_result the judge's label came from -------------------------------

def owner_verdict(check: str, grades: dict[str, tuple[str, str]]) -> JudgeVerdict:
    if check == "answer":
        points = sorted(((int(match.group(1)), value) for item, (value, _note) in grades.items()
                        if (match := POINT_ITEM.match(item))))
        unsupported = grades["unsupported claims"][0]
        return JudgeVerdict(required_points=tuple(value for _, value in points),
                            contradicts_ground_truth=grades["contradicts ground truth"][0].strip().lower() in ("yes", "true"),
                            unsupported_claims=() if unsupported.strip().lower() in ("no", "none", "") else (unsupported,))
    return JudgeVerdict(presents_related_as_answer=grades["presents_related_as_answer"][0].strip().lower() in ("yes", "true"))


def owner_label(sid: str, check: str, grades: dict, record: dict) -> str:
    verdict = owner_verdict(check, grades)
    try:
        return map_result(record["answerable"], record["insufficient"], has_related_note(record), bool(record["citations"]), verdict)
    except ValueError as error:  # JudgeVerdictMissing (needs a call) or a bad coverage value - both mean a malformed grade
        raise SpotCheckError(f"{sid}: {error}") from error


def holistic_agreement(grades: dict[str, tuple[str, str]]) -> bool:
    return grades[HOLISTIC_ITEM][0].strip().lower() == "yes"


# --- joining the sheet, the key and the run records --------------------------------------------------------------

def load_records_by_key(key: dict[str, dict], root: Path = PROJECT_ROOT) -> dict[str, dict]:
    """{sid: record} - the full-mode `records.jsonl` entry each key entry points to (full mode is the only mode a
    judge check ever runs on)."""
    runs: dict[str, dict] = {}
    records = {}
    for sid, entry in key.items():
        run_id = entry["run_id"]
        if run_id not in runs:
            runs[run_id] = load_run(run_id, root=root)
        matches = [r for r in runs[run_id]["records"] if r["case_id"] == entry["case_id"] and r["arm"] == entry["arm"]
                  and r["mode"] == "full"]
        if not matches:
            raise SpotCheckError(f"{sid}: no full-mode record for {entry['case_id']}:{entry['arm']} in run {run_id}")
        records[sid] = matches[-1]
    return records


def rule_based_pairs(cases: dict[str, dict], key: dict[str, dict], records: dict[str, dict]) -> list[tuple[str, str, str]]:
    """[(sid, judge_label, owner_label), ...], one per S-id present in both the sheet and the key (sorted). Raises
    if the two disagree on which S-ids exist - a partial join would silently under-count the sample."""
    only_key, only_sheet = sorted(set(key) - set(cases)), sorted(set(cases) - set(key))
    if only_key or only_sheet:
        raise SpotCheckError(f"S-id mismatch between sheet and key: only in key {only_key or '(none)'}, "
                             f"only in sheet {only_sheet or '(none)'}")
    return [(sid, key[sid]["label"], owner_label(sid, cases[sid]["check"], cases[sid]["grades"], records[sid]))
           for sid in sorted(cases, key=lambda s: int(s[1:]))]


# --- scoring (pure) ------------------------------------------------------------------------------------------

def agreement_rate(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    agree = sum(1 for judge, human in pairs if judge == human)
    return {"n": n, "count": agree, "value": agree / n if n else None}


def cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Chance-corrected agreement: (p_o - p_e) / (1 - p_e); `None` for an empty sheet, 1.0 for perfect agreement on
    a single shared label (`p_e` is then 1 too - there is no chance to correct for, so treat it as full agreement)."""
    from collections import Counter
    n = len(pairs)
    if n == 0:
        return None
    labels = sorted({label for pair in pairs for label in pair})
    judge_counts, human_counts = Counter(judge for judge, _ in pairs), Counter(human for _, human in pairs)
    p_o = sum(1 for judge, human in pairs if judge == human) / n
    p_e = sum((judge_counts[label] / n) * (human_counts[label] / n) for label in labels)
    if p_e >= 1:
        return 1.0
    return (p_o - p_e) / (1 - p_e)


def confusion_matrix(pairs: list[tuple[str, str]]) -> tuple[list[str], dict[str, dict[str, int]]]:
    labels = sorted({label for pair in pairs for label in pair})
    matrix = {judge: dict.fromkeys(labels, 0) for judge in labels}
    for judge, human in pairs:
        matrix[judge][human] += 1
    return labels, matrix


def disagreements(pairs: list[tuple[str, str, str]], cases: dict[str, dict], key: dict[str, dict]) -> list[dict]:
    return [{"sid": sid, "judge_label": judge_label, "owner_label": owner_label_, "judge_reason": key[sid]["reason"],
             "owner_note": cases[sid]["grades"][HOLISTIC_ITEM][1] or "(no note)"}
           for sid, judge_label, owner_label_ in pairs if judge_label != owner_label_]


# --- rendering ---------------------------------------------------------------------------------------------

def render_section(sheet_path: Path, key_path: Path, cases: dict[str, dict], key: dict[str, dict],
                   pairs: list[tuple[str, str, str]]) -> str:
    rule_pairs = [(judge, owner) for _, judge, owner in pairs]
    agreement = agreement_rate(rule_pairs)
    kappa = cohens_kappa(rule_pairs)
    labels, matrix = confusion_matrix(rule_pairs)
    caption = (f"Sheet: `{sheet_path}`, key: `{key_path}`. {len(pairs)} case(s), scored rule-based: the owner's "
              "per-point grades run through the same `metrics.mapping.map_result` the judge's label came from.")
    summary_table = md_table(("metric", "value"), [
        ("agreement (rule-based)", f"{agreement['value']:.3f} ({agreement['count']}/{agreement['n']})"
         if agreement["value"] is not None else "– (n=0)"),
        ("Cohen's kappa", f"{kappa:.3f}" if kappa is not None else "–"),
    ])
    matrix_table = md_table(("judge \\ owner",) + tuple(labels),
                            [(judge,) + tuple(str(matrix[judge][human]) for human in labels) for judge in labels])
    bad = disagreements(pairs, cases, key)
    disagreement_lines = ([f"- {d['sid']}: judge={d['judge_label']}, owner={d['owner_label']} "
                           f"(judge: {d['judge_reason'] or '(no reason)'}; owner: {d['owner_note']})" for d in bad]
                          or ["(none)"])
    holistic_no = sorted((sid for sid in cases if not holistic_agreement(cases[sid]["grades"])),
                         key=lambda s: int(s[1:]))
    holistic_yes = len(cases) - len(holistic_no)
    secondary = (f"Holistic \"agree with the judge?\" column (self-reported, ignores `map_result`): "
                f"{holistic_yes}/{len(cases)}" + (f", disagreeing: {', '.join(holistic_no)}" if holistic_no else "") + ".")
    return "\n\n".join([caption, summary_table, "Confusion matrix (rows = judge label, columns = owner via "
                        "map_result):", matrix_table, "Disagreements (rule-based):",
                        "\n".join(disagreement_lines), secondary])


# --- CLI ------------------------------------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sheet", type=Path, metavar="SHEET_FILE", help="the owner's blind grading sheet (never modified)")
    parser.add_argument("key", type=Path, metavar="KEY_FILE", help="the judge's verdicts + S-id key (never modified)")
    parser.add_argument("--out", type=Path, default=None, help=f"report path (default {DEFAULT_OUT})")
    return parser.parse_args(argv)


def _resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def main(argv=None, *, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        sheet_path = args.sheet if args.sheet.is_absolute() else Path.cwd() / args.sheet
        key_path = args.key if args.key.is_absolute() else Path.cwd() / args.key
        cases = parse_owner_sheet(sheet_path.read_text(encoding="utf-8"))
        check_filled(cases)
        key = parse_key(key_path.read_text(encoding="utf-8"))
        records = load_records_by_key(key, root)
        pairs = rule_based_pairs(cases, key, records)

        report_path = _resolve(args.out or DEFAULT_OUT, root)
        report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "# EPIC-05 evaluation report (generated)\n"
        section = render_section(sheet_path, key_path, cases, key, pairs)
        report_text = replace_or_append_section(report_text, JUDGE_AGREEMENT_NAME, JUDGE_AGREEMENT_TITLE, section)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8", newline="\n")

        print(f"scored {len(pairs)} case(s); report: {report_path}", file=out)
        return EXIT_OK
    except (SpotCheckError, EvaluationError, OSError) as error:
        print(f"ABORTED: {error}", file=err)
        return EXIT_ABORTED


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
