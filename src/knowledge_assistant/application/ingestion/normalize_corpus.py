"""Ingestion use case: accepted documents from the manifest -> parse -> normalize (ADR-0003 D1).

Depends on core interfaces only; the script wires the infrastructure parser registry and normalizer.
"""
import hashlib
import json
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from knowledge_assistant.core.interfaces.normalizer import DocumentNormalizer
from knowledge_assistant.core.interfaces.parser import DocumentParser
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, Document, ParsedDocument


def load_accepted_documents(manifest_path: Path, project_root: Path) -> list[Document]:
    """Only `documents` (accepted) are returned. Excluded IDs and files under corpus/excluded are refused."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    excluded_ids = {entry["source_id"] for entry in manifest.get("excluded", [])}
    documents = []
    for entry in manifest["documents"]:
        relative = PurePosixPath(entry["file"])
        if entry["source_id"] in excluded_ids or "excluded" in relative.parts:
            raise ValueError(f"manifest lists excluded document #{entry['source_id']} ({entry['file']}) as accepted")
        documents.append(
            Document(
                source_id=entry["source_id"],
                name=entry["title"],
                path=str(project_root / relative),
                source_url=entry.get("source_url"),
            )
        )
    return documents


class NormalizeCorpus:
    def __init__(self, parser_for: Callable[[str], DocumentParser], normalizer: DocumentNormalizer) -> None:
        self._parser_for = parser_for
        self._normalizer = normalizer

    def run(self, documents: Iterable[Document]) -> list[ParsedDocument]:
        results = []
        for document in documents:
            parsed = self._parser_for(Path(document.path).suffix).parse(document)
            results.append(self._normalizer.normalize(parsed))
        return results


def to_record(document: ParsedDocument, file: str) -> dict:
    """One `normalized.jsonl` line: id, metadata, text, sha256 (of the UTF-8 normalized text)."""
    return {
        "id": document.source_id,
        "metadata": {
            "document_name": document.document_name,
            "source_url": document.source_url,
            "wrapper_title": document.wrapper_title,
            "file": file,
            "sections": [
                {
                    "heading_path": HEADING_PATH_SEPARATOR.join(section.heading_path),
                    "heading_parts": list(section.heading_path),
                    "level": section.level,
                    "variant": section.variant,
                    "variant_count": section.variant_count,
                    "char_start": section.char_start,
                    "char_end": section.char_end,
                }
                for section in document.sections
            ],
        },
        "text": document.text,
        "sha256": hashlib.sha256(document.text.encode("utf-8")).hexdigest(),
    }


def write_jsonl(records: Iterable[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8", newline="\n"
    )


def unlocated_inventory_sections(records: Iterable[dict], inventory_rows: Iterable[dict]) -> list[dict]:
    """Inventory sections (source_id, heading path, variant) with no matching span in the normalized text.

    A span matches when it has the same heading path and variant, and the text at its start is that heading line.
    """
    spans = {}
    for record in records:
        for section in record["metadata"]["sections"]:
            key = (record["id"], section["heading_path"], section["variant"])
            spans[key] = (record["text"], section)
    missing = []
    for row in inventory_rows:
        found = spans.get((row["source_id"], row["heading_path"], row["variant"]))
        if found is None:
            missing.append(row)
            continue
        text, section = found
        heading = "#" * row["level"] + " " + row["heading_parts"][-1]
        if not text[section["char_start"] : section["char_end"]].startswith(heading):
            missing.append(row)
    return missing
