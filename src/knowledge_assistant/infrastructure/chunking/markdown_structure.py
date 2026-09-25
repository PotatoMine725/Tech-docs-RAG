"""Markdown heading structure shared by corpus analysis and the chunkers (ADR-0003 D2).

Headings are ATX headings (`#` .. `######`) outside fenced code blocks. Sections start at
H1-H3; H4+ stays inside its parent section. Line numbers are 0-based indexes into `lines`.
"""
import re
from collections.abc import Sequence
from dataclasses import dataclass

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$")
_CLOSING_HASHES = re.compile(r"[ \t]+#+$")
_SOURCE = re.compile(r"^Source:\s*(\S+)")
SECTION_LEVELS = 3


@dataclass(frozen=True)
class Heading:
    level: int
    text: str
    line: int


@dataclass(frozen=True)
class Section:
    heading_path: tuple[str, ...]
    level: int
    start_line: int
    end_line: int  # exclusive


@dataclass(frozen=True)
class PageFrame:
    """The web-export wrapper around a page: `# <wrapper title>`, `Source: <url>`, then the page's own H1."""

    wrapper_title: str
    source_url: str | None
    page_title: str
    page_title_line: int


def find_headings(lines: Sequence[str]) -> list[Heading]:
    headings: list[Heading] = []
    fence: str | None = None
    for index, line in enumerate(lines):
        opener = _FENCE.match(line)
        if fence is not None:
            if opener and _closes(fence, line, opener.group(1)):
                fence = None
            continue
        if opener:
            fence = opener.group(1)
            continue
        match = _ATX.match(line)
        if match:
            text = _CLOSING_HASHES.sub("", match.group(2) or "")
            if text == "#" * len(text):  # a bare closing sequence such as "## ##"
                text = ""
            headings.append(Heading(len(match.group(1)), text.strip(), index))
    return headings


def _closes(fence: str, line: str, marker: str) -> bool:
    same_kind = marker[0] == fence[0] and len(marker) >= len(fence)
    return same_kind and line.strip() == marker


def split_sections(lines: Sequence[str], start_line: int = 0) -> list[Section]:
    starts = [h for h in find_headings(lines) if h.line >= start_line and h.level <= SECTION_LEVELS]
    path: dict[int, str] = {}
    sections: list[Section] = []
    for position, heading in enumerate(starts):
        path[heading.level] = heading.text
        for deeper in range(heading.level + 1, SECTION_LEVELS + 1):
            path.pop(deeper, None)
        end = starts[position + 1].line if position + 1 < len(starts) else len(lines)
        heading_path = tuple(path[level] for level in sorted(path) if level <= heading.level)
        sections.append(Section(heading_path, heading.level, heading.line, end))
    return sections


def read_page_frame(lines: Sequence[str]) -> PageFrame:
    h1s = [h for h in find_headings(lines) if h.level == 1]
    if len(h1s) < 2:
        raise ValueError("expected a wrapper H1 followed by the page's own H1")
    wrapper, page = h1s[0], h1s[1]
    source_url = None
    for line in lines[wrapper.line + 1 : page.line]:
        match = _SOURCE.match(line.strip())
        if match:
            source_url = match.group(1)
            break
    return PageFrame(wrapper.text, source_url, page.text, page.line)


def fence_mask(lines: Sequence[str]) -> list[bool]:
    """True for every line that is a fence line or inside a fenced code block (same rules as `find_headings`)."""
    mask: list[bool] = []
    fence: str | None = None
    for line in lines:
        opener = _FENCE.match(line)
        if fence is not None:
            mask.append(True)
            if opener and _closes(fence, line, opener.group(1)):
                fence = None
            continue
        if opener:
            fence = opener.group(1)
            mask.append(True)
            continue
        mask.append(False)
    return mask


def fenced_ranges(text: str) -> list[tuple[int, int]]:
    """Character spans `[start, end)` of fenced code blocks, fence lines included (same rules as `fence_mask`)."""
    lines = text.split("\n")
    ranges: list[tuple[int, int]] = []
    offset = 0
    block_start: int | None = None
    for line, fenced in zip(lines, fence_mask(lines)):
        if fenced and block_start is None:
            block_start = offset
        elif not fenced and block_start is not None:
            ranges.append((block_start, offset - 1))
            block_start = None
        offset += len(line) + 1
    if block_start is not None:
        ranges.append((block_start, len(text)))
    return ranges
