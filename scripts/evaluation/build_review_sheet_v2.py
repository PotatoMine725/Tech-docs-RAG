"""Refresh the case tables of the benchmark v2 owner review sheet from eval-v2.jsonl / dev-v2.jsonl.

Reuses the cell helpers of build_review_sheet.py (v1, unchanged). Rewrites only the text between the
`<!-- CASES START -->` and `<!-- CASES END -->` markers of docs/reviews/evaluation/eval-v2-review.md and keeps the
owner's decisions: the Decision and Note cells of a row are carried over by question ID on every refresh.
Run: .venv/Scripts/python.exe scripts/evaluation/build_review_sheet_v2.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_review_sheet as v1  # noqa: E402  (v1 helpers, reused read-only)

QUESTIONS = v1.QUESTIONS
SHEET = v1.PROJECT_ROOT / "docs" / "reviews" / "evaluation" / "eval-v2-review.md"
START, END = v1.START, v1.END
CATEGORY_TITLES = {
    "A_vi_on_vi": "A: Vietnamese question, Vietnamese document",
    "B_en_on_en": "B: English question, English document",
    "C_vi_on_en": "C: Vietnamese question, English document",
    "D_vi_on_mixed": "D: Vietnamese question, mixed VI-EN document",
    "E_identifier_c1": "E: exact identifier, corpus 1",
    "F_unanswerable": "F: unanswerable (not in the documents)",
}
ROW_ID = re.compile(r"^\| (Q2-(?:EVAL|DEV)-\d{3}) \|")


def _evidence(case: dict) -> str:
    if not case["answerable"]:
        return f"absence proof {case['absence_proof']} (`evidence-map-v2.yaml`)"
    return v1._evidence(case)


def _previous_decisions(text: str) -> dict:
    """{question id: (decision, note)} from the rows currently in the sheet."""
    decisions = {}
    for line in text.splitlines():
        match = ROW_ID.match(line)
        if match:
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
            decisions[match.group(1)] = (cells[-2], cells[-1])
    return decisions


def _display(case: dict) -> dict:
    """Copy of the case with heading path "" shown as "(whole document)" (ADR-0008)."""
    fix = lambda refs: [{**r, "heading_path": r["heading_path"] or "(whole document)"} for r in refs]
    return {**case, **{k: fix(case[k]) for k in ("expected_sources", "acceptable_alternate_sources", "evidence")}}


def table(cases: list[dict], decisions: dict) -> str:
    head = ("| ID | Lang · typing | Question | Expected answer (required points bold) | Expected source · heading path "
            "| Evidence quote(s) | Decision | Note |\n|---|---|---|---|---|---|---|---|\n")
    rows = []
    for c in map(_display, cases):
        decision, note = decisions.get(c["id"], ("☐ approve / fix / reject", ""))
        rows.append(f"| {c['id']} | {c['language']} · {c['typing']} | {v1._question_cell(c['question'])} | "
                    f"{v1._answer(c)} | {v1._sources(c)} | {_evidence(c)} | {decision} | {note} |")
    return head + "\n".join(rows) + "\n"


def render_cases(decisions: dict) -> str:
    parts = []
    for split, title in (("eval", "Evaluation set v2"), ("dev", "Dev set v2 (tuning only, never reported)")):
        cases = v1_read(QUESTIONS / f"{split}-v2.jsonl")
        if split == "dev":
            parts.append(f"### {title} ({len(cases)})\n\n{table(cases, decisions)}")
            continue
        for category, name in CATEGORY_TITLES.items():
            group = [c for c in cases if c["category"] == category]
            if group:
                parts.append(f"### {title} · {name} ({len(group)})\n\n{table(group, decisions)}")
    return "\n".join(parts)


def v1_read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    text = SHEET.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers not found in {SHEET}")
    decisions = _previous_decisions(text)
    new = pattern.sub(lambda _: f"{START}\n{render_cases(decisions)}{END}", text)
    with SHEET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(new)
    print(f"refreshed {SHEET.relative_to(v1.PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
