"""Domain models. Fields marked TBD are intentionally undecided (see docs/architecture/data-model.md)."""
from dataclasses import dataclass

from knowledge_assistant.core.interfaces.llm import LLMResponse

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
class RetrievedChunk:
    """One search hit. `score` is a similarity (higher = more similar); for cosine, 1 - distance."""

    chunk: DocumentChunk
    rank: int  # 1-based
    score: float
    duplicate_chunk_ids: tuple[str, ...] = ()  # same-passage hits this one replaced in dedup (RAG-002, owner 2026-09-26)


@dataclass(frozen=True)
class Citation:
    source_id: str
    document_name: str
    location: str  # heading path (ADR-0003 D5); never a page number
    excerpt: str  # original English chunk text (ADR-0003 D9)
    chunk_id: str
    marker: int  # the [n] passage number in the prompt and the answer (1..k)
    source_url: str  # "" when the document has none (all 24 accepted documents have one)
    location_type: str = "heading"  # extensible: heading | position (documents without headings)


@dataclass(frozen=True)
class AnswerResult:
    """One answered question (RAG-002). When `insufficient`, `answer` is the localized message and `citations`
    are optional related content only, never support for an answer (owner decision D2, 2026-09-24)."""

    question: str
    language: str  # "en" | "vi"
    answer: str
    insufficient: bool
    insufficient_reason: str | None  # "retrieval_gate" | "llm" | None
    missing_information: str | None
    citations: tuple[Citation, ...]  # ordered by first marker in the answer, then the LLM's cited_passages
    retrieved: tuple[RetrievedChunk, ...]
    dropped_markers: tuple[int, ...]  # [n] markers / cited passages that pointed outside 1..k
    uncited_sentences: int  # diagnostic: sentences of >= 5 words without any marker
    latency_ms: dict[str, float]  # embed_query, retrieve, generate, total
    llm: LLMResponse | None  # None when the retrieval gate fired
    prompt_version: str
    duplicates_dropped: int = 0  # over-fetched hits dropped as same-content duplicates (RAG-002 addendum 1)


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
