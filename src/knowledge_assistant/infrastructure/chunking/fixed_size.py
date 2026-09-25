"""Arm B: fixed-size chunker (ADR-0003 D7). Character windows of `size_chars`, consecutive windows overlap by
`overlap_chars`; no structure is respected. Heading path = the section containing the chunk start (D5)."""
from dataclasses import dataclass

from knowledge_assistant.core.models import DocumentChunk, ParsedDocument
from knowledge_assistant.infrastructure.chunking.chunk_builder import (
    ChunkingResult,
    Span,
    build_chunks,
    section_path_at,
    trim,
)


@dataclass(frozen=True)
class FixedSizeConfig:
    chunker_config: str
    size_chars: int
    overlap_chars: int

    def __post_init__(self) -> None:
        if not 0 <= self.overlap_chars < self.size_chars:
            raise ValueError("overlap_chars must be >= 0 and smaller than size_chars")


class FixedSizeChunker:
    def __init__(self, config: FixedSizeConfig) -> None:
        self.config = config

    def chunk(self, document: ParsedDocument) -> list[DocumentChunk]:
        return self.chunk_with_report(document).chunks

    def chunk_with_report(self, document: ParsedDocument) -> ChunkingResult:
        return build_chunks(document, self.spans(document), self.config.chunker_config)

    def spans(self, document: ParsedDocument) -> list[Span]:
        text = document.text
        step = self.config.size_chars - self.config.overlap_chars
        spans: list[Span] = []
        window = 0
        while window < len(text):
            end = min(window + self.config.size_chars, len(text))
            start, stop = trim(text, window, end)
            if start < stop:
                spans.append(Span(start, stop, section_path_at(document, start)))
            if end == len(text):
                break
            window += step
        return spans
