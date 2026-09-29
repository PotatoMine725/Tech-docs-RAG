"""INGEST-002: normalized.jsonl -> documents -> chunk files (the committed files equal a fresh run)."""
import json
import sys
from pathlib import Path

import pytest

from knowledge_assistant.application.ingestion.build_chunks import CHUNK_FIELDS, from_record, load_normalized_documents
from knowledge_assistant.application.ingestion.normalize_corpus import to_record

ROOT = Path(__file__).resolve().parents[3]
NORMALIZED = ROOT / "data" / "processed" / "documents" / "normalized.jsonl"
CHUNKS = ROOT / "data" / "processed" / "chunks"


def _build(arm: str):
    sys.path.insert(0, str(ROOT / "scripts" / "ingestion"))
    try:
        from build_chunks import build
    finally:
        sys.path.pop(0)
    return build(arm)


def test_from_record_is_the_inverse_of_to_record():
    record = json.loads(NORMALIZED.read_text(encoding="utf-8").splitlines()[0])
    assert to_record(from_record(record), record["metadata"]["file"]) == record


def test_all_24_accepted_documents_are_loaded():
    documents = load_normalized_documents(NORMALIZED)
    assert len(documents) == 24
    assert not {d.source_id for d in documents} & {"14", "19", "24", "25", "27"}


@pytest.mark.parametrize("arm", ["A", "B"])
def test_committed_chunk_and_stats_files_equal_a_fresh_run(arm):
    records, stats = _build(arm)
    committed = [json.loads(line) for line in (CHUNKS / f"arm-{arm.lower()}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert committed == records
    assert json.loads((CHUNKS / f"stats-arm-{arm.lower()}.json").read_text(encoding="utf-8")) == stats
    assert all(tuple(record) == CHUNK_FIELDS for record in records)
