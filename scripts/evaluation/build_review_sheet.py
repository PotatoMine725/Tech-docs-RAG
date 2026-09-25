"""Refresh the case tables of the EVAL-002 human review sheet from the question files.

Rewrites only the text between the `<!-- CASES START -->` and `<!-- CASES END -->` markers in
docs/reviews/evaluation/eval-v1-review.md; the checklist, notes and verdict lines above stay as written.
Run after any wording or ground-truth correction: .venv/Scripts/python.exe scripts/evaluation/build_review_sheet.py
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
SHEET = PROJECT_ROOT / "docs" / "reviews" / "evaluation" / "eval-v1-review.md"
START, END = "<!-- CASES START -->", "<!-- CASES END -->"


def _cell(text: str, code: bool = False) -> str:
    text = text.replace("|", "\\|")
    if not code:  # bare <T> would render as an HTML tag; code spans show it literally
        text = text.replace("<", "&lt;")
    return text.replace("\n", "<br>")


def _question_cell(question: str) -> str:
    """Code fences can't live in a table cell: show fenced code as inline code lines."""
    if "```" not in question:
        return _cell(question)
    prose, *code = [line for line in question.split("\n") if not line.startswith("```")]
    return "<br>".join([_cell(prose)] + [_cell(f"`{line}`", code=True) for line in code])


def _sources(case: dict) -> str:
    rows = [f"**{s['slot']}** #{s['source_id']} {s['heading_path']}" for s in case["expected_sources"]]
    rows += [f"alt {a['slot']} #{a['source_id']} {a['heading_path']}" for a in case["acceptable_alternate_sources"]]
    return _cell("\n".join(rows)) if rows else "— (not in the documents)"


def _evidence(case: dict) -> str:
    if not case["evidence"]:
        return f"absence proof {case['absence_proof']} (`evidence-map.yaml`)" if case["absence_proof"] else "—"
    return _cell("\n".join(f"[{','.join(e['supports'])}] #{e['source_id']}: \"{e['quote']}\"" for e in case["evidence"]))


def _answer(case: dict) -> str:
    if not case["answerable"]:
        return "Refuse: " + _cell(case["expected_behavior"]) + "<br>must not claim: " + _cell("; ".join(case["must_not_claim"]))
    return _cell("\n".join(f"{'**' + p['id'] + '**' if p['required'] else p['id'] + ' (opt)'}: {p['text']}"
                           for p in case["answer_points"]))


def table(cases: list[dict]) -> str:
    head = "| ID | Lang | Group | Question | Expected answer (required points bold) | Expected source · heading path | Evidence quote(s) | OK? |\n"
    head += "|---|---|---|---|---|---|---|---|\n"
    rows = [f"| {c['id']} | {c['language']} | {c['parallel_group_id'] or '—'} | {_question_cell(c['question'])} | "
            f"{_answer(c)} | {_sources(c)} | {_evidence(c)} | ☐ |" for c in cases]
    return head + "\n".join(rows) + "\n"


def render_cases() -> str:
    parts = []
    for split, title in (("eval", "Evaluation set (36)"), ("dev", "Dev set (6, tuning only, never reported)")):
        cases = [json.loads(line) for line in (QUESTIONS / f"{split}-v1.jsonl").read_text(encoding="utf-8").splitlines()]
        parts.append(f"### {title}\n\n{table(cases)}")
    return "\n".join(parts)


def main() -> int:
    text = SHEET.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers not found in {SHEET}")
    new = pattern.sub(lambda _: f"{START}\n{render_cases()}{END}", text)
    with SHEET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(new)
    print(f"refreshed {SHEET.relative_to(PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
