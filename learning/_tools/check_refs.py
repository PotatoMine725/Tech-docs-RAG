"""Check `path:line` references and verbatim snippets in learning/*.md (offline, read-only).

1. Every block that follows a header line **`path:a-b`** must equal lines a..b of that file.
2. Every inline `path:line` / `path:a-b` (path with a known extension) must point inside an existing file.
3. Every topic file must carry the pinned commit SHA.
Exit code 1 when anything fails.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _pin import read_lines  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEARN = ROOT / "learning"
PIN = "762b754"
HEADER = re.compile(r"^\*\*`([^`:]+):(\d+)-(\d+)`\*\*$")
INLINE = re.compile(r"`([\w./\-]+\.(?:py|md|json|toml|txt|yml|yaml|jsonl|example|sha256)):(\d+)(?:-(\d+))?`")
REPO_REF = re.compile(r"\[REPO ([\w./\-]+\.[A-Za-z0-9]+):(\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)\]")
_cache = {}


def file_lines(rel):
    if rel not in _cache:
        p = ROOT / rel
        _cache[rel] = p.read_text(encoding="utf-8").split("\n") if p.is_file() else None
    return _cache[rel]


def check(path):
    problems = []
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if path.name[0].isdigit() and PIN not in "\n".join(lines[:6]):
        problems.append(f"{path.name}: pinned commit {PIN} missing in the first lines")
    i = 0
    while i < len(lines):
        m = HEADER.match(lines[i])
        if m:
            rel, a, b = m.group(1), int(m.group(2)), int(m.group(3))
            src = file_lines(rel)
            if src is None:
                problems.append(f"{path.name}:{i+1}: snippet file {rel} not found")
            elif i + 1 >= len(lines) or not lines[i + 1].startswith("```"):
                problems.append(f"{path.name}:{i+1}: no code fence after snippet header")
            else:
                j = i + 2
                block = []
                while j < len(lines) and lines[j] != "```":
                    block.append(lines[j])
                    j += 1
                if block != src[a - 1 : b]:
                    problems.append(f"{path.name}:{i+1}: snippet {rel}:{a}-{b} differs from the file")
                i = j
        i += 1
    for n, line in enumerate(lines, start=1):
        if HEADER.match(line):
            continue
        for m in list(INLINE.finditer(line)) + list(REPO_REF.finditer(line)):
            rel = m.group(1).replace("\\", "/")
            if m.re is INLINE:
                pieces = [m.group(2) + ("-" + m.group(3) if m.group(3) else "")]
            else:
                pieces = m.group(2).split(",")  # "35-37,76-79" -> two ranges
            src = file_lines(rel)
            if src is None:
                if "/" in rel:  # a bare file name is not a repo path
                    problems.append(f"{path.name}:{n}: {rel} is not tracked at the pinned commit")
                continue
            for piece in pieces:
                a, _, b = piece.partition("-")
                a, b = int(a), int(b or a)
                if not 1 <= a <= b <= len(src):
                    problems.append(f"{path.name}:{n}: {rel}:{piece} outside the file ({len(src)} lines)")
    return problems


def main():
    files = sorted(p for p in LEARN.glob("*.md") if not p.name.startswith("_"))
    bad = []
    for f in files:
        bad += check(f)
    print(f"checked {len(files)} files, {len(bad)} problem(s)")
    for p in bad:
        print(" -", p)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
