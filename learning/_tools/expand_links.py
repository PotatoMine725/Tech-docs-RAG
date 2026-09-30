"""Expand `@@LINK NN|keyword@@` in learning/_src/glossary.md into `[NN §x.y](NN-file.md)` links and write learning/glossary.md.

`keyword` must match exactly one heading (case-insensitive substring) of the final learning/NN-*.md file, so a renamed or
missing section fails loudly instead of leaving a dead link. Run after expand_snippets.py.
    PYTHONDONTWRITEBYTECODE=1 python learning/_tools/expand_links.py
"""
import re
import sys
from pathlib import Path

LEARNING = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"@@LINK (\w+)\|([^@]+)@@")
HEADING = re.compile(r"^#{2,4} (?:(\d+\.\d+|T\d+) ?·? ?)?(.*)$")


def headings(number: str) -> tuple[Path, list[tuple[str, str]]]:
    matches = sorted(LEARNING.glob(f"{number}-*.md"))
    if len(matches) != 1:
        raise SystemExit(f"file {number}: expected exactly one match, got {matches}")
    found = []
    for line in matches[0].read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#{2,4} (.*)$", line)
        if m:
            text = m.group(1)
            num = re.match(r"^(\d+\.\d+|T\d+)\b", text)
            found.append((num.group(1) if num else "", text))
    return matches[0], found


def resolve(match: re.Match, errors: list[str]) -> str:
    number, keyword = match.group(1), match.group(2).strip()
    path, found = headings(number)
    hits = [(n, t) for n, t in found if keyword.lower() in t.lower()]
    if len(hits) != 1:
        errors.append(f"@@LINK {number}|{keyword}@@ matched {len(hits)} headings: {[t for _, t in hits][:4]}")
        return match.group(0)
    section = hits[0][0]
    label = f"{number} §{section}" if section else number
    return f"[{label}]({path.name})"


def main() -> int:
    source = LEARNING / "_src" / "glossary.md"
    errors: list[str] = []
    text = TOKEN.sub(lambda m: resolve(m, errors), source.read_text(encoding="utf-8"))
    if errors:
        print("\n".join(errors))
        return 1
    (LEARNING / "glossary.md").write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote glossary.md ({len(text.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
