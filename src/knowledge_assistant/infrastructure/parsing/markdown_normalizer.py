"""ADR-0003 D1 normalization of web-exported Markdown pages (in memory; sources are never written).

Steps, in order:
1. `\\r\\n` / `\\r` -> `\\n` first, because offsets and hashes depend on it (a BOM is dropped too).
2. Everything before the page's own H1 (wrapper H1, `Source:` URL, `---`, access notes, #29's YAML
   front matter) moves to metadata or is dropped. An unknown preamble line raises instead of being dropped.
3. Known boilerplate lines are removed outside code fences (`BOILERPLATE_LINES`, from the EPIC-01 report and
   ADR-0003 measured facts), with the admonition label or footer rule that belongs to them.
4. Runs of blank lines outside code fences collapse to one.
Version variants are kept and numbered 1..n by repeated heading path; version labels are never inferred.
"""
import hashlib
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from knowledge_assistant.core.exceptions import DocumentParseError
from knowledge_assistant.core.models import ParsedDocument, SectionSpan
from knowledge_assistant.infrastructure.chunking.markdown_structure import fence_mask, read_page_frame, split_sections

# Whole lines (stripped) removed wherever they appear outside code fences. Source: EPIC-01 corpus report
# ("Wrapper", boilerplate list) and ADR-0003 "Measured corpus facts"; counts are per document.
BOILERPLATE_LINES = (
    re.compile(r"^Access to this page requires authorization\. You can try .*changing directories\.$"),  # 19 docs
    re.compile(r"^This isn't the latest version of this article\. "),  # #10 #11 #12 #13 #23
    re.compile(r"^This version of ASP\.NET Core is no longer supported\. "),  # #10 #11 #12 #13 #23
    re.compile(r"^By \[[^\]]+\]\([^)]*\)"),  # author bylines: #03 #10 #13 #17 #23
)
_LAST_UPDATED = re.compile(r"^- Last updated on\s*$")  # page footer, 19 docs; the next line is the date
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ADMONITION_LABEL = re.compile(r"^(Note|Warning|Important|Tip|Caution)$")
_RULE = re.compile(r"^-{3,}$")
_SOURCE = re.compile(r"^Source:\s*\S+$")
_FRONT_MATTER_KEY = re.compile(r"^[A-Za-z][\w.-]*:(\s|$)")


class MarkdownNormalizer:
    def normalize(self, document: ParsedDocument) -> ParsedDocument:
        text = document.text.replace("\r\n", "\n").replace("\r", "\n").removeprefix("﻿")
        lines = text.split("\n")
        try:
            frame = read_page_frame(lines)
        except ValueError as error:
            raise DocumentParseError(f"#{document.source_id}: {error}") from error
        _check_preamble(document.source_id, lines[: frame.page_title_line])

        body = _drop_boilerplate(lines[frame.page_title_line :])
        normalized = "\n".join(_collapse_blank_lines(body)).strip("\n") + "\n"
        return replace(
            document,
            text=normalized,
            document_name=frame.page_title,
            source_url=frame.source_url,
            wrapper_title=frame.wrapper_title,
            sections=section_spans(normalized),
            normalized=True,
        )


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def section_spans(text: str) -> tuple[SectionSpan, ...]:
    """H1-H3 sections of normalized text with character spans and variant numbers (as in the section inventory)."""
    lines = text.split("\n")
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line) + 1)
    sections = split_sections(lines)
    repeats = Counter(s.heading_path for s in sections)
    seen: Counter = Counter()
    spans = []
    for section in sections:
        seen[section.heading_path] += 1
        spans.append(
            SectionSpan(
                heading_path=section.heading_path,
                level=section.level,
                variant=seen[section.heading_path],
                variant_count=repeats[section.heading_path],
                char_start=starts[section.start_line],
                char_end=min(starts[section.end_line], len(text)),
            )
        )
    return tuple(spans)


def _check_preamble(source_id: str, preamble: Sequence[str]) -> None:
    """Everything before the page H1 is wrapper or boilerplate; anything else is an error, not a silent drop."""
    in_front_matter = False
    for index, raw in enumerate(preamble):
        line = raw.strip()
        if _RULE.match(line) and index + 1 < len(preamble) and _FRONT_MATTER_KEY.match(preamble[index + 1].strip()):
            in_front_matter = True
            continue
        if in_front_matter:
            if _RULE.match(line):
                in_front_matter = False
            elif not _FRONT_MATTER_KEY.match(line):
                raise DocumentParseError(f"#{source_id}: unexpected front-matter line {index + 1}: {line!r}")
            continue
        known = (
            not line
            or (index == 0 and line.startswith("# "))
            or _SOURCE.match(line)
            or _RULE.match(line)
            or _ADMONITION_LABEL.match(line)
            or _is_boilerplate(line)
        )
        if not known:
            raise DocumentParseError(f"#{source_id}: unexpected preamble line {index + 1}: {line!r}")


def _is_boilerplate(line: str) -> bool:
    return any(pattern.match(line) for pattern in BOILERPLATE_LINES)


def _drop_boilerplate(lines: list[str]) -> list[str]:
    in_code = fence_mask(lines)
    drop = [False] * len(lines)

    def next_content(index: int) -> int | None:
        for later in range(index + 1, len(lines)):
            if lines[later].strip():
                return later
        return None

    for index, line in enumerate(lines):
        if in_code[index]:
            continue
        stripped = line.strip()
        if _is_boilerplate(stripped):
            drop[index] = True
        elif _LAST_UPDATED.match(stripped):
            drop[index] = True
            following = next_content(index)
            if following is not None and not in_code[following] and _DATE.match(lines[following].strip()):
                drop[following] = True
    # Labels and footer rules that only introduce a removed line go with it.
    for index, line in enumerate(lines):
        if in_code[index] or drop[index]:
            continue
        stripped = line.strip()
        following = next_content(index)
        if following is None or not drop[following]:
            continue
        if _ADMONITION_LABEL.match(stripped) and _is_boilerplate(lines[following].strip()):
            drop[index] = True
        elif _RULE.match(stripped) and _LAST_UPDATED.match(lines[following].strip()):
            drop[index] = True
    return [line for line, dropped in zip(lines, drop) if not dropped]


def _collapse_blank_lines(lines: list[str]) -> list[str]:
    in_code = fence_mask(lines)
    kept: list[str] = []
    for line, code in zip(lines, in_code):
        if not code and not line.strip() and kept and not kept[-1].strip():
            continue
        kept.append("" if not code and not line.strip() else line)
    return kept
