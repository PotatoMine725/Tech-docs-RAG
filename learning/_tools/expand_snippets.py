"""Expand `@@SNIP path a-b@@` lines in learning/_src/*.md into verbatim, line-numbered code blocks.

Usage (from the worktree root): python learning/_tools/expand_snippets.py [file ...]
Output goes to learning/<same name>. Snippets are copied byte-for-byte from the git blob at the pinned commit (not the working tree).
A snippet may be at most 25 lines. Offline; reads repo files only; writes only inside learning/.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _pin import read_lines  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "learning" / "_src"
OUT = ROOT / "learning"
DIRECTIVE = re.compile(r"^@@SNIP (\S+) (\d+)-(\d+)@@\s*$")
LANG = {".py": "python", ".md": "markdown", ".json": "json", ".toml": "toml", ".txt": "text", ".example": "text"}


def expand(text: str, name: str) -> str:
    out = []
    for number, line in enumerate(text.splitlines(), start=1):
        m = DIRECTIVE.match(line)
        if not m:
            out.append(line)
            continue
        rel, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        lines = (ROOT / rel).read_text(encoding="utf-8").split("\n")
        if not 1 <= a <= b <= len(lines):
            raise SystemExit(f"{name}:{number}: {rel}:{a}-{b} out of range (file has {len(lines)} lines)")
        if b - a + 1 > 25:
            raise SystemExit(f"{name}:{number}: snippet {rel}:{a}-{b} is longer than 25 lines")
        lang = LANG.get(pathlib.Path(rel).suffix, "text")
        out.append(f"**`{rel}:{a}-{b}`**")
        out.append(f"```{lang}")
        out.extend(lines[a - 1 : b])
        out.append("```")
    return "\n".join(out) + "\n"


def main(argv):
    files = [SRC / a for a in argv] if argv else sorted(p for p in SRC.glob("*.md") if p.name != "glossary.md")  # glossary uses expand_links.py
    for f in files:
        (OUT / f.name).write_text(expand(f.read_text(encoding="utf-8"), f.name), encoding="utf-8", newline="\n")
        print("wrote", f.name)


if __name__ == "__main__":
    main(sys.argv[1:])
