"""Arm A: header-aware chunker (ADR-0003 D2-D5).

1. Sections are the H1-H3 spans of the normalized document (H4+ stays inside its parent, D2).
2. A section shorter than `min_chars` merges with the next section when that section is a sibling (same parent
   heading path, same level) and the merged text still fits `max_chars`; the merged chunk keeps the first
   section's heading path (D3).
3. A section longer than `max_chars` is cut into blocks: paragraphs, fenced code blocks, tables (atomic) and
   heading lines. Blocks are packed greedily into pieces. A single block longer than `max_chars` is split: code
   by lines, tables by rows (the header row is repeated in `embed_text` only, so `display_text` stays an exact
   slice of the normalized text), paragraphs by sentences, and a too-long sentence at whitespace (D4).
4. Consecutive pieces of one split section overlap by up to `overlap_chars`, never across sections (D4). The
   overlap starts at a word boundary, never inside a code fence, and is shortened so a piece stays within
   `max_chars`.
"""
import re
from dataclasses import dataclass

from knowledge_assistant.core.models import DocumentChunk, ParsedDocument
from knowledge_assistant.infrastructure.chunking.chunk_builder import ChunkingResult, Span, build_chunks, trim
from knowledge_assistant.infrastructure.chunking.markdown_structure import fence_mask, fenced_ranges

_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=\S)")


@dataclass(frozen=True)
class HeaderAwareConfig:
    chunker_config: str
    max_chars: int
    min_chars: int
    overlap_chars: int

    def __post_init__(self) -> None:
        if not 0 <= self.overlap_chars < self.max_chars or not 0 <= self.min_chars <= self.max_chars:
            raise ValueError("need 0 <= overlap_chars < max_chars and 0 <= min_chars <= max_chars")


@dataclass(frozen=True)
class _Unit:
    start: int
    end: int
    kind: str  # heading | text | code | table
    table_header: str = ""  # set on a table-row group that does not contain the header row itself


class HeaderAwareChunker:
    def __init__(self, config: HeaderAwareConfig) -> None:
        self.config = config

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        return self.chunk_with_report(document).chunks

    def chunk_with_report(self, document: ParsedDocument) -> ChunkingResult:
        return build_chunks(document, self.spans(document), self.config.chunker_config)

    def spans(self, document: ParsedDocument) -> list[Span]:
        text = document.text
        layout = _Layout(text)
        spans: list[Span] = []
        for start, end, path in self._groups(document):
            start, end = trim(text, start, end)
            if start >= end:
                continue
            if end - start <= self.config.max_chars:
                spans.append(Span(start, end, path))
            else:
                spans.extend(self._split(layout, start, end, path))
        return spans

    # --- step 2: merge small sections with their next sibling ------------------------------------------------

    def _groups(self, document: ParsedDocument) -> list[tuple[int, int, tuple[str, ...]]]:
        text = document.text
        sections = document.sections
        if not sections:
            return [(0, len(text), ())]
        groups = []
        index = 0
        while index < len(sections):
            first = sections[index]
            start, end = first.char_start, first.char_end
            index += 1
            while index < len(sections) and _size(text, start, end) < self.config.min_chars:
                following = sections[index]
                sibling = following.level == first.level and following.heading_path[:-1] == first.heading_path[:-1]
                if not sibling or _size(text, start, following.char_end) > self.config.max_chars:
                    break
                end = following.char_end
                index += 1
            groups.append((start, end, first.heading_path))
        return groups

    # --- steps 3-4: split an oversized section --------------------------------------------------------------

    def _split(self, layout: "_Layout", start: int, end: int, path: tuple[str, ...]) -> list[Span]:
        maximum, overlap = self.config.max_chars, self.config.overlap_chars
        pieces: list[list[_Unit]] = []
        current: list[_Unit] = []
        for unit in self._units(layout, start, end):
            budget = maximum if not pieces else maximum - overlap
            if current and unit.end - current[0].start > budget:
                carried = []
                heading_last = len(current) > 1 and current[-1].kind == "heading"
                if heading_last and unit.end - current[-1].start <= maximum - overlap:
                    carried = [current.pop()]  # keep a heading with the block that follows it
                pieces.append(current)
                current = carried
            current.append(unit)
        if current:
            pieces.append(current)

        spans: list[Span] = []
        previous_start = previous_end = -1
        for piece in pieces:
            content_start, content_end = piece[0].start, piece[-1].end
            piece_start = content_start
            if spans:
                room = min(overlap, maximum - (content_end - previous_end))
                if room > 0:
                    piece_start = layout.overlap_start(max(previous_end - room, previous_start), previous_end)
                    if piece_start >= previous_end:
                        piece_start = content_start
            spans.append(Span(piece_start, content_end, path, piece[0].table_header))
            previous_start, previous_end = piece_start, content_end
        return spans

    def _units(self, layout: "_Layout", start: int, end: int) -> list[_Unit]:
        """Blocks of `text[start:end]`; a block longer than `max_chars` is split into sub-units."""
        limit = self.config.max_chars - self.config.overlap_chars
        units: list[_Unit] = []
        for kind, lines in layout.blocks(start, end):
            block_start = max(layout.line_starts[lines[0]], start)
            block_end = min(layout.line_end(lines[-1]), end)
            if block_end - block_start <= self.config.max_chars:
                units.append(_Unit(block_start, block_end, kind))
            elif kind == "code":
                ranges = [(layout.line_starts[i], layout.line_end(i)) for i in lines]
                units.extend(_Unit(s, e, kind) for s, e in _pack(layout.text, ranges, limit))
            elif kind == "table":
                units.extend(self._table_units(layout, lines, limit))
            else:
                ranges = _sentences(layout.text, block_start, block_end)
                units.extend(_Unit(s, e, kind) for s, e in _pack(layout.text, ranges, limit))
        return units

    def _table_units(self, layout: "_Layout", lines: list[int], limit: int) -> list[_Unit]:
        header_lines = lines[:2] if len(lines) > 1 and _TABLE_SEPARATOR.match(layout.lines[lines[1]]) else lines[:1]
        header = "".join(layout.lines[i] + "\n" for i in header_lines)
        ranges = [(layout.line_starts[i], layout.line_end(i)) for i in lines]
        # the first group starts with the header row itself; later groups get it repeated in embed_text only
        groups = _pack(layout.text, ranges, limit)
        return [_Unit(s, e, "table", "" if n == 0 else header) for n, (s, e) in enumerate(groups)]


class _Layout:
    """Line table of one normalized document: line starts, fence mask, fence char ranges."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.lines = text.split("\n")
        self.line_starts = []
        offset = 0
        for line in self.lines:
            self.line_starts.append(offset)
            offset += len(line) + 1
        self.fenced = fence_mask(self.lines)
        self.fences = fenced_ranges(text)

    def line_end(self, index: int) -> int:
        return self.line_starts[index] + len(self.lines[index])

    def line_index(self, position: int) -> int:
        low, high = 0, len(self.line_starts) - 1
        while low < high:
            middle = (low + high + 1) // 2
            if self.line_starts[middle] <= position:
                low = middle
            else:
                high = middle - 1
        return low

    def blocks(self, start: int, end: int) -> list[tuple[str, list[int]]]:
        """(kind, line indexes) for the lines touching `[start, end)`; blank lines separate blocks."""
        first, last = self.line_index(start), self.line_index(max(start, end - 1))
        blocks: list[tuple[str, list[int]]] = []
        index = first
        while index <= last:
            line = self.lines[index]
            if self.fenced[index]:
                kind, test = "code", lambda i: self.fenced[i]
            elif not line.strip():
                index += 1
                continue
            elif _HEADING.match(line):
                blocks.append(("heading", [index]))
                index += 1
                continue
            elif line.lstrip().startswith("|"):
                kind, test = "table", lambda i: not self.fenced[i] and self.lines[i].lstrip().startswith("|")
            else:
                kind, test = "text", self._is_paragraph_line
            following = index + 1
            while following <= last and test(following):
                following += 1
            blocks.append((kind, list(range(index, following))))
            index = following
        return blocks

    def _is_paragraph_line(self, index: int) -> bool:
        line = self.lines[index]
        return (
            not self.fenced[index] and bool(line.strip()) and not _HEADING.match(line) and not line.lstrip().startswith("|")
        )

    def overlap_start(self, candidate: int, previous_end: int) -> int:
        """First word start at or after `candidate` that is not inside a code fence (>= previous_end: none).
        Inside a table row the overlap starts at the next row, so a piece never starts in the middle of a row."""
        text, position = self.text, candidate
        line = self.line_index(position)
        if self.lines[line].lstrip().startswith("|") and not self.fenced[line] and position > self.line_starts[line]:
            position = self.line_starts[line + 1] if line + 1 < len(self.lines) else previous_end
        elif position > 0 and not text[position - 1].isspace():
            while position < previous_end and not text[position].isspace():
                position += 1
        for fence_start, fence_end in self.fences:
            if fence_start < position < fence_end:
                position = fence_end
        while position < previous_end and text[position].isspace():
            position += 1
        return position


def _size(text: str, start: int, end: int) -> int:
    trimmed_start, trimmed_end = trim(text, start, end)
    return trimmed_end - trimmed_start


def _sentences(text: str, start: int, end: int) -> list[tuple[int, int]]:
    ranges, cursor = [], start
    for match in _SENTENCE_END.finditer(text, start, end):
        ranges.append((cursor, match.start()))
        cursor = match.end()
    ranges.append((cursor, end))
    return ranges


def _pack(text: str, ranges: list[tuple[int, int]], limit: int) -> list[tuple[int, int]]:
    """Greedily join consecutive ranges into groups of at most `limit` chars; a longer range is cut at whitespace."""
    groups: list[tuple[int, int]] = []
    for range_start, range_end in ranges:
        for start, end in _cut(text, range_start, range_end, limit):
            if groups and end - groups[-1][0] <= limit:
                groups[-1] = (groups[-1][0], end)
            else:
                groups.append((start, end))
    return groups


def _cut(text: str, start: int, end: int, limit: int) -> list[tuple[int, int]]:
    pieces = []
    while end - start > limit:
        cut = text.rfind(" ", start + 1, start + limit)
        cut = cut if cut > start else start + limit
        pieces.append((start, cut))
        start = cut
        while start < end and text[start].isspace():
            start += 1
    if start < end:
        pieces.append((start, end))
    return pieces
