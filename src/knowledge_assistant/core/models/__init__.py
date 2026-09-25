"""Domain models. Fields marked TBD are intentionally undecided (see docs/architecture/data-model.md)."""
from dataclasses import dataclass

HEADING_PATH_SEPARATOR = " > "


@dataclass(frozen=True)
class Document:
    """A source document to ingest (format-independent reference)."""

    source_id: str
    name: str
    path: str = ""
    source_url: str | None = None


@dataclass(frozen=True)
class SectionSpan:
    """One H1-H3 section of a normalized document (ADR-0003 D2); offsets index `ParsedDocument.text`."""

    heading_path: tuple[str, ...]
    level: int
    variant: int  # 1..n among sections with the same heading path (version variants, ADR-0003 D1)
    variant_count: int
    char_start: int
    char_end: int  # exclusive


@dataclass(frozen=True)
class ParsedDocument:
    """Markdown text of one document. Raw after parsing; `normalized=True` after ADR-0003 D1 normalization."""

    document: Document
    text: str
    document_name: str = ""
    source_url: str | None = None
    wrapper_title: str = ""
    sections: tuple[SectionSpan, ...] = ()
    normalized: bool = False

    @property
    def source_id(self) -> str:
        return self.document.source_id


@dataclass(frozen=True)
class DocumentChunk:
    """Exactly the ADR-0003 D6 fields."""

    chunk_id: str  # {source_id}:{chunker_config}:{index:04d}
    source_id: str
    document_name: str
    source_url: str | None
    heading_path: tuple[str, ...]
    location_type: str
    char_start: int  # offsets into the normalized text
    char_end: int
    display_text: str
    embed_text: str
    content_hash: str
    chunker_config: str


@dataclass(frozen=True)
class Citation:
    source_id: str
    document_name: str
    location: str  # heading path (ADR-0003 D5); never a page number
    excerpt: str
    location_type: str = "heading"  # extensible: heading | position (documents without headings)


@dataclass(frozen=True)
class Question:
    text: str


@dataclass(frozen=True)
class EvaluationCase:
    question: Question


@dataclass(frozen=True)
class EvaluationResult:
    case: EvaluationCase


@dataclass(frozen=True)
class Experiment:
    name: str
