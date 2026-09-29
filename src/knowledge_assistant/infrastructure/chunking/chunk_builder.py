"""Shared by both experiment arms (ADR-0003 D5/D6): contextual header, link stripping, IDs, duplicate drop.

A chunker only decides spans (character ranges of the normalized text plus a heading path); this module turns
spans into `DocumentChunk`s the same way for every arm, so both arms emit identical fields.
"""
import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass

from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, DocumentChunk, ParsedDocument
from knowledge_assistant.infrastructure.chunking.markdown_structure import fenced_ranges

LOCATION_TYPE = "heading"  # ADR-0003 D5: the heading path is the citation location
# [text](url) and ![alt](url), with an optional "title"; one level of parentheses inside the URL.
_LINK = re.compile(r"!?\[([^\]\n]*)\]\((?:[^()\s]|\([^()\s]*\))*(?:\s+\"[^\"\n]*\")?\)")


@dataclass(frozen=True)
class Span:
    """A chunk before it gets an ID. `embed_prefix` is text only the embedding sees (a repeated table header)."""

    start: int
    end: int  # exclusive
    heading_path: tuple[str, ...]
    embed_prefix: str = ""


@dataclass(frozen=True)
class ChunkingResult:
    chunks: list[DocumentChunk]
    duplicates_dropped: int


def trim(text: str, start: int, end: int) -> tuple[int, int]:
    """Move `start` forward and `end` back over whitespace, so a chunk never starts or ends with blank space."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def section_path_at(document: ParsedDocument, position: int) -> tuple[str, ...]:
    """Heading path of the H1-H3 section that contains `position` (the nearest heading before it)."""
    starts = [section.char_start for section in document.sections]
    index = bisect_right(starts, position) - 1
    return document.sections[index].heading_path if index >= 0 else ()


def strip_links(text: str, start: int, end: int, fences: list[tuple[int, int]]) -> str:
    """`text[start:end]` with Markdown links reduced to their text; code fences are copied unchanged."""
    parts: list[str] = []
    cursor = start
    for fence_start, fence_end in fences:
        if fence_end <= cursor or fence_start >= end:
            continue
        if fence_start > cursor:
            parts.append(_LINK.sub(r"\1", text[cursor:fence_start]))
        cursor = max(cursor, fence_start)
        parts.append(text[cursor : min(fence_end, end)])
        cursor = min(fence_end, end)
    if cursor < end:
        parts.append(_LINK.sub(r"\1", text[cursor:end]))
    return "".join(parts)


def content_hash(display_text: str) -> str:
    return hashlib.sha256(display_text.encode("utf-8")).hexdigest()


def build_chunks(document: ParsedDocument, spans: list[Span], chunker_config: str) -> ChunkingResult:
    """Spans -> chunks in order. A chunk whose text hash equals an earlier chunk of the same document is dropped
    (ADR-0003 D1); IDs are numbered after the drop, so they stay contiguous and deterministic."""
    if ":" in chunker_config:
        raise ValueError(f"chunker_config must not contain ':' (it is part of the chunk ID): {chunker_config!r}")
    text = document.text
    fences = fenced_ranges(text)
    chunks: list[DocumentChunk] = []
    seen: set[str] = set()
    dropped = 0
    for span in spans:
        display_text = text[span.start : span.end]
        if not display_text.strip():
            continue
        digest = content_hash(display_text)
        if digest in seen:
            dropped += 1
            continue
        seen.add(digest)
        heading_line = HEADING_PATH_SEPARATOR.join(span.heading_path)
        body = _LINK.sub(r"\1", span.embed_prefix) + strip_links(text, span.start, span.end, fences)
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document.source_id}:{chunker_config}:{len(chunks):04d}",
                source_id=document.source_id,
                document_name=document.document_name,
                source_url=document.source_url,
                heading_path=span.heading_path,
                location_type=LOCATION_TYPE,
                char_start=span.start,
                char_end=span.end,
                display_text=display_text,
                embed_text=f"{heading_line}\n\n{body}" if heading_line else body,
                content_hash=digest,
                chunker_config=chunker_config,
            )
        )
    return ChunkingResult(chunks, dropped)
