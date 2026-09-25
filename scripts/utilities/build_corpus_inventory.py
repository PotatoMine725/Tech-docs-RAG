"""Build the corpus manifest and section inventory (EPIC-01 / CORPUS-001).

Writes:
- corpus/manifest.json: one entry per accepted document (corpus/sources/).
- data/processed/documents/section-inventory.jsonl: one line per H1-H3 section (ADR-0003 D2).

Reads only corpus/sources/. Excluded documents are listed by file name and never opened.
Text is read with LF line endings, so every number and hash is the same on any checkout.
Output is deterministic: re-running on unchanged sources produces identical files.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.infrastructure.chunking.markdown_structure import (  # noqa: E402
    find_headings,
    read_page_frame,
    split_sections,
)

SOURCES = PROJECT_ROOT / "corpus" / "sources"
EXCLUDED = PROJECT_ROOT / "corpus" / "excluded"
MANIFEST = PROJECT_ROOT / "corpus" / "manifest.json"
INVENTORY = PROJECT_ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
PATH_SEPARATOR = " > "
_INDEX_PAGE = (
    "Index page: links to other pages, no content useful to the assistant "
    "(stated by the project owner, 2026-09-24, OD-3)"
)
EXCLUDED_REASONS = {"14": _INDEX_PAGE, "19": _INDEX_PAGE, "24": _INDEX_PAGE, "27": _INDEX_PAGE}


def _source_id(path: Path) -> str:
    return path.name.split("-")[0]


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _document(path: Path) -> tuple[dict, list[dict]]:
    text = path.read_text(encoding="utf-8")  # universal newlines: CRLF becomes LF
    lines = text.split("\n")
    frame = read_page_frame(lines)
    sections = split_sections(lines, start_line=frame.page_title_line)
    levels = Counter(min(h.level, 4) for h in find_headings(lines[frame.page_title_line :]))
    repeats = Counter(s.heading_path for s in sections)
    source_id = _source_id(path)

    seen: Counter = Counter()
    rows = []
    for index, section in enumerate(sections):
        seen[section.heading_path] += 1
        rows.append(
            {
                "source_id": source_id,
                "section_index": index,
                "heading_path": PATH_SEPARATOR.join(section.heading_path),
                "heading_parts": list(section.heading_path),
                "level": section.level,
                "variant": seen[section.heading_path],
                "variant_count": repeats[section.heading_path],
                "line_start": section.start_line + 1,
                "line_end": section.end_line,
                "chars": len("\n".join(lines[section.start_line : section.end_line])),
            }
        )

    entry = {
        "source_id": source_id,
        "file": _relative(path),
        "title": frame.page_title,
        "wrapper_title": frame.wrapper_title,
        "source_url": frame.source_url,
        "chars": len(text),
        "lines": len(lines),
        "sha256_lf": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "preamble_chars": len("\n".join(lines[: frame.page_title_line])),
        "headings": {"h2": levels[2], "h3": levels[3], "h4_plus": levels[4]},
        "sections": len(sections),
        "distinct_heading_paths": len(repeats),
        "max_heading_path_repeats": max(repeats.values()),
    }
    return entry, rows


def build() -> tuple[dict, list[dict]]:
    documents, inventory = [], []
    for path in sorted(SOURCES.glob("*.md")):
        entry, rows = _document(path)
        documents.append(entry)
        inventory.extend(rows)

    excluded = [
        {"source_id": _source_id(p), "file": _relative(p), "reason": EXCLUDED_REASONS[_source_id(p)]}
        for p in sorted(EXCLUDED.glob("*.md"))
    ]
    known = {d["source_id"] for d in documents} | {e["source_id"] for e in excluded}
    highest = max(int(i) for i in known)
    manifest = {
        "description": "Accepted documents of the Knowledge Assistant corpus. Sources are read-only originals.",
        "generated_by": "scripts/utilities/build_corpus_inventory.py",
        "text_note": (
            "chars, lines and sha256_lf use the file text with LF line endings (as stored in git). "
            "docs/snapshots/corpus/ holds SHA-256 of the original CRLF bytes."
        ),
        "section_inventory": _relative(INVENTORY),
        "counts": {"original": len(known), "accepted": len(documents), "excluded": len(excluded)},
        "never_existed_ids": [f"{i:02d}" for i in range(1, highest + 1) if f"{i:02d}" not in known],
        "excluded": excluded,
        "documents": documents,
    }
    return manifest, inventory


def main() -> None:
    manifest, inventory = build()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in inventory), encoding="utf-8", newline="\n"
    )
    print(f"{len(manifest['documents'])} documents, {len(inventory)} sections")
    print(f"wrote {_relative(MANIFEST)} and {_relative(INVENTORY)}")


if __name__ == "__main__":
    main()
