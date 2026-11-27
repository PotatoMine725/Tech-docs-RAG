"""Refresh the case table of the dev-v3 owner review sheet from dev-v3.jsonl.

Rewrites only the text between the `<!-- CASES START -->` and `<!-- CASES END -->` markers of
docs/reviews/evaluation/dev-v3-review.md and keeps the owner's "owner: ok / change" cell of each row (by question ID).
One row per question: question, expected answer in one line, source + heading path, evidence quote(s).
Run: .venv/Scripts/python.exe scripts/evaluation/build_review_sheet_v3.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_review_sheet as v1  # noqa: E402  (v1 helpers, reused read-only)

QUESTIONS = v1.QUESTIONS
SHEET = v1.PROJECT_ROOT / "docs" / "reviews" / "evaluation" / "dev-v3-review.md"
START, END = v1.START, v1.END
ROW_ID = re.compile(r"^\| (Q3-DEV-\d{3}) \|")
EMPTY = " "


def _one_line(text: str) -> str:
    return v1._cell(" ".join(text.split()))


def _source(case: dict) -> str:
    if not case["answerable"]:
        near = ", ".join(f"#{s}" for s in case["near_miss_sources"])
        return f"— (not in the documents; near: {near})"
    return "<br>".join(_one_line(f"#{s['source_id']} {s['heading_path'] or '(whole document / preamble)'}")
                       for s in case["expected_sources"])


def _evidence(case: dict, proofs: dict) -> str:
    if not case["answerable"]:
        proof = proofs.get(case["absence_proof"], {})
        terms = ", ".join(f"`{t}`" for t in proof.get("zero_hit_terms", []))
        return f"{case['absence_proof']}: zero hits for {terms}"
    return "<br>".join(_one_line(f"[{','.join(e['supports'])}] \"{e['quote']}\"") for e in case["evidence"])


def _answer(case: dict) -> str:
    if not case["answerable"]:
        return "Refuse (not in the documents). Must not claim: " + _one_line("; ".join(case["must_not_claim"]))
    return _one_line(case["expected_answer"])


def _previous_decisions(text: str) -> dict:
    decisions = {}
    for line in text.splitlines():
        match = ROW_ID.match(line)
        if match:
            decisions[match.group(1)] = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]][-1]
    return decisions


def table(cases: list[dict], proofs: dict, decisions: dict) -> str:
    head = ("| ID | Lang · typing · difficulty | Question | Expected answer (one line) | Source · heading path "
            "| Evidence quote(s) | owner: ok / change |\n|---|---|---|---|---|---|---|\n")
    rows = [f"| {c['id']} | {c['question_language']} · {c['typing']} · {c['difficulty']} | {_one_line(c['question'])} | "
            f"{_answer(c)} | {_source(c)} | {_evidence(c, proofs)} | {decisions.get(c['id'], EMPTY) or EMPTY} |"
            for c in cases]
    return head + "\n".join(rows) + "\n"


def main() -> int:
    import yaml

    cases = [__import__("json").loads(l) for l in (QUESTIONS / "dev-v3.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    proofs = {p["id"]: p for p in yaml.safe_load((QUESTIONS / "evidence-map-v3.yaml").read_text(encoding="utf-8"))["absence_proofs"]}
    text = SHEET.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"markers not found in {SHEET}")
    new = pattern.sub(lambda _: f"{START}\n{table(cases, proofs, _previous_decisions(text))}{END}", text)
    with SHEET.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(new)
    print(f"refreshed {SHEET.relative_to(v1.PROJECT_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
