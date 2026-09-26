"""Ingestion use case, second half: normalized documents -> chunk records (INGEST-002, ADR-0003 D6).

Depends on core only; `scripts/ingestion/build_chunks.py` wires the chunker chosen by `--arm`.
"""
import json
from pathlib import Path

from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, Document, DocumentChunk, ParsedDocument, SectionSpan

CHUNK_FIELDS = (
    "chunk_id",
    "source_id",
    "document_name",
    "source_url",
    "heading_path",
    "location_type",
    "char_start",
    "char_end",
    "display_text",
    "embed_text",
    "content_hash",
    "chunker_config",
)


def from_record(record: dict) -> ParsedDocument:
    """Inverse of `normalize_corpus.to_record`: one `normalized.jsonl` line -> a normalized `ParsedDocument`."""
    metadata = record["metadata"]
    sections = tuple(
        SectionSpan(
            heading_path=tuple(section["heading_parts"]),
            level=section["level"],
            variant=section["variant"],
            variant_count=section["variant_count"],
            char_start=section["char_start"],
            char_end=section["char_end"],
        )
        for section in metadata["sections"]
    )
    return ParsedDocument(
        document=Document(
            source_id=record["id"],
            name=metadata["document_name"],
            path=metadata["file"],
            source_url=metadata["source_url"],
        ),
        text=record["text"],
        document_name=metadata["document_name"],
        source_url=metadata["source_url"],
        wrapper_title=metadata["wrapper_title"],
        sections=sections,
        normalized=True,
    )


def load_normalized_documents(path: Path) -> list[ParsedDocument]:
    return [from_record(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]


def chunk_to_record(chunk: DocumentChunk) -> dict:
    """One chunk-file line: exactly the D6 fields; the heading path is stored as its citation string."""
    record = {field: getattr(chunk, field) for field in CHUNK_FIELDS}
    record["heading_path"] = HEADING_PATH_SEPARATOR.join(chunk.heading_path)
    return record


def record_to_chunk(record: dict) -> DocumentChunk:
    """Inverse of `chunk_to_record`: one chunk-file line -> a `DocumentChunk` (heading path split back)."""
    values = {field: record[field] for field in CHUNK_FIELDS}
    heading = values["heading_path"]
    values["heading_path"] = tuple(heading.split(HEADING_PATH_SEPARATOR)) if heading else ()
    return DocumentChunk(**values)


def load_chunks(path: Path) -> list[DocumentChunk]:
    """Read a chunk file written by `scripts/ingestion/build_chunks.py` (`arm-a.jsonl`, `arm-b.jsonl`)."""
    return [record_to_chunk(json.loads(line)) for line in path.read_text(encoding="utf-8").splitlines() if line]
