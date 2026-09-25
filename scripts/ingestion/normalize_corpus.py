"""Normalize the accepted corpus -> data/processed/documents/normalized.jsonl (INGEST-001, ADR-0003 D1).

Reads only the documents listed as accepted in corpus/manifest.json; sources are never written.
Also checks that every section-inventory heading path has a character span in the normalized text
(needed for section hit@5) and exits 1 if any cannot be located.
Deterministic: re-running on unchanged sources produces an identical file.
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.normalize_corpus import (  # noqa: E402
    NormalizeCorpus,
    load_accepted_documents,
    to_record,
    unlocated_inventory_sections,
    write_jsonl,
)
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import MarkdownNormalizer  # noqa: E402
from knowledge_assistant.infrastructure.parsing.registry import default_registry  # noqa: E402

MANIFEST = PROJECT_ROOT / "corpus" / "manifest.json"
INVENTORY = PROJECT_ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
OUTPUT = PROJECT_ROOT / "data" / "processed" / "documents" / "normalized.jsonl"


def build() -> list[dict]:
    documents = load_accepted_documents(MANIFEST, PROJECT_ROOT)
    normalized = NormalizeCorpus(default_registry().get, MarkdownNormalizer()).run(documents)
    return [
        to_record(doc, Path(source.path).relative_to(PROJECT_ROOT).as_posix())
        for doc, source in zip(normalized, documents)
    ]


def main() -> int:
    records = build()
    write_jsonl(records, OUTPUT)
    inventory = [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines() if line]
    missing = unlocated_inventory_sections(records, inventory)
    raw_chars = sum(len((PROJECT_ROOT / r["metadata"]["file"]).read_text(encoding="utf-8")) for r in records)
    print(f"{len(records)} documents, {sum(len(r['text']) for r in records):,} normalized chars (raw LF {raw_chars:,})")
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"inventory heading paths located: {len(inventory) - len(missing)}/{len(inventory)}")
    for row in missing:
        print(f"  NOT LOCATED: #{row['source_id']} {row['heading_path']} (variant {row['variant']})")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
