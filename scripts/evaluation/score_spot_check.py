"""EVAL-003c: score a filled judge spot-check sheet (owner review of `evaluation-spec.md` § "Limitation": the judge
is the same model as the answer model).

    python scripts/evaluation/score_spot_check.py FILE [--out PATH]

Reads a sheet written by `make_spot_check.py` (one `## case_id (arm ..., language)` section per sampled case, each
with a `Judge result` field and a blank `human_result` field for the owner to fill). Refuses to run - no output
written - while any `human_result` is still blank, so a half-filled sheet can never silently produce a score.

Computes, over every case in the sheet: the raw agreement rate (judge result == human result), Cohen's kappa
(chance-corrected agreement), the confusion matrix (judge vs human) and the list of disagreements with the owner's
`human_note`. Writes them into `--out` (default `docs/reports/epics/EPIC-05-evaluation.md`, matching
`make_tables.py`) between `<!-- AUTO:judge_agreement --> ... <!-- /AUTO:judge_agreement -->` markers - the same
markers `make_tables.py` seeds with a placeholder, now filled in. Text outside the markers is never touched.

Zero Gemini requests: offline, reads only the local sheet file.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
for _extra in (PROJECT_ROOT / "src", PROJECT_ROOT):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

from knowledge_assistant.application.evaluation.metrics.mapping import (  # noqa: E402
    CORRECT,
    CORRECT_REFUSAL,
    FALSE_REFUSAL,
    HALLUCINATION,
    INCORRECT,
    PARTIALLY_CORRECT,
)

from scripts.evaluation.make_tables import (  # noqa: E402
    JUDGE_AGREEMENT_NAME,
    JUDGE_AGREEMENT_TITLE,
    DEFAULT_OUT,
    md_table,
    replace_or_append_section,
)

RESULT_LABELS = (CORRECT, PARTIALLY_CORRECT, INCORRECT, FALSE_REFUSAL, CORRECT_REFUSAL, HALLUCINATION)
EXIT_OK, EXIT_ABORTED = 0, 3

CASE_HEADER = re.compile(r"^## (?P<case_id>\S+) \(arm (?P<arm>\S+), (?P<language>\S+)\)\s*$", re.MULTILINE)
FIELD = re.compile(r"^- \*\*([^:*]+):\*\* ?(.*)$", re.MULTILINE)
RUN_ID = re.compile(r"<!-- run_id: (\S+) -->")


class SpotCheckError(ValueError):
    """The sheet is missing data score_spot_check.py needs (a blank human_result, an unparseable case, ...)."""


# --- parsing (pure) --------------------------------------------------------------------------------------------

def parse_sheet(text: str) -> list[dict]:
    """One dict per `## case_id (arm ..., language)` section, with every `- **Field:** value` line as a key.
    Split on a line starting with `## `: every field value the sheet writes is collapsed to one line by
    `make_spot_check.py`, so a `##` inside quoted corpus text (mid-line) can never be mistaken for a case heading.
    """
    chunks = re.split(r"(?m)^## ", text)
    cases = []
    for chunk in chunks[1:]:  # chunks[0] is the file header before the first case
        chunk = "## " + chunk
        header = CASE_HEADER.match(chunk)
        if not header:
            raise SpotCheckError(f"cannot parse a case heading: {chunk.splitlines()[0]!r}")
        fields = {name.strip(): value.strip() for name, value in FIELD.findall(chunk)}
        cases.append({"case_id": header["case_id"], "arm": header["arm"], "language": header["language"], **fields})
    return cases


def run_id_from_sheet(text: str) -> str:
    match = RUN_ID.search(text)
    if not match:
        raise SpotCheckError("sheet has no <!-- run_id: ... --> marker (not written by make_spot_check.py?)")
    return match.group(1)


def check_filled(cases: list[dict]) -> None:
    blank = sorted(case["case_id"] for case in cases if not case.get("human_result", "").strip())
    if blank:
        raise SpotCheckError(f"human_result is blank for: {', '.join(blank)} - fill every case before scoring")
    unknown = sorted({(case["case_id"], case["human_result"]) for case in cases
                      if case["human_result"] not in RESULT_LABELS})
    if unknown:
        pairs = ", ".join(f"{case_id}={value!r}" for case_id, value in unknown)
        raise SpotCheckError(f"human_result must be one of {RESULT_LABELS}, got: {pairs}")


# --- scoring (pure) ----------------------------------------------------------------------------------------

def judge_human_pairs(cases: list[dict]) -> list[tuple[str, str]]:
    return [(case["Judge result"], case["human_result"]) for case in cases]


def agreement_rate(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    agree = sum(1 for judge, human in pairs if judge == human)
    return {"n": n, "count": agree, "value": agree / n if n else None}


def cohens_kappa(pairs: list[tuple[str, str]]) -> float | None:
    """Chance-corrected agreement: (p_o - p_e) / (1 - p_e); `None` for an empty sheet, 1.0 for perfect agreement on
    a single shared label (`p_e` is then 1 too - there is no chance to correct for, so treat it as full agreement)."""
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


def disagreements(cases: list[dict]) -> list[dict]:
    return [case for case in cases if case["Judge result"] != case["human_result"]]


# --- rendering ---------------------------------------------------------------------------------------------

def render_section(sheet_path: Path, run_id: str, cases: list[dict]) -> str:
    pairs = judge_human_pairs(cases)
    agreement = agreement_rate(pairs)
    kappa = cohens_kappa(pairs)
    labels, matrix = confusion_matrix(pairs)
    caption = f"Sheet: `{sheet_path}` (run `{run_id}`). {len(cases)} case(s) scored by the owner."
    summary_table = md_table(("metric", "value"), [
        ("agreement", f"{agreement['value']:.3f} ({agreement['count']}/{agreement['n']})" if agreement["value"] is not None else "– (n=0)"),
        ("Cohen's kappa", f"{kappa:.3f}" if kappa is not None else "–"),
    ])
    matrix_table = md_table(("judge \\ human",) + tuple(labels),
                            [(judge,) + tuple(str(matrix[judge][human]) for human in labels) for judge in labels])
    bad = disagreements(cases)
    if bad:
        disagreement_lines = [f"- {case['case_id']} (arm {case['arm']}, {case['language']}): judge={case['Judge result']}, "
                              f"human={case['human_result']}"
                              + (f" — {case['human_note']}" if case.get("human_note") else "")
                              for case in bad]
    else:
        disagreement_lines = ["(none)"]
    return "\n\n".join([caption, summary_table, "Confusion matrix (rows = judge result, columns = human result):",
                        matrix_table, "Disagreements:", "\n".join(disagreement_lines)])


# --- CLI ------------------------------------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], epilog=__doc__.split("\n\n", 1)[1],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", type=Path, metavar="FILE", help="a spot-check sheet written by make_spot_check.py")
    parser.add_argument("--out", type=Path, default=None, help=f"report path (default {DEFAULT_OUT})")
    return parser.parse_args(argv)


def _resolve(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


def main(argv=None, *, root: Path = PROJECT_ROOT, out=None, err=None) -> int:
    args = parse_args(argv)
    out, err = out or sys.stdout, err or sys.stderr
    try:
        sheet_path = args.file if args.file.is_absolute() else Path.cwd() / args.file
        text = sheet_path.read_text(encoding="utf-8")
        cases = parse_sheet(text)
        check_filled(cases)
        run_id = run_id_from_sheet(text)

        report_path = _resolve(args.out or DEFAULT_OUT, root)
        report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "# EPIC-05 evaluation report (generated)\n"
        section = render_section(sheet_path, run_id, cases)
        report_text = replace_or_append_section(report_text, JUDGE_AGREEMENT_NAME, JUDGE_AGREEMENT_TITLE, section)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_text, encoding="utf-8", newline="\n")

        print(f"scored {len(cases)} case(s); report: {report_path}", file=out)
        return EXIT_OK
    except (SpotCheckError, OSError) as error:
        print(f"ABORTED: {error}", file=err)
        return EXIT_ABORTED


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    sys.exit(main())
