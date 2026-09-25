"""INGEST-001: ingestion use case over the real corpus (offline, deterministic)."""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

from knowledge_assistant.application.ingestion.normalize_corpus import (
    NormalizeCorpus,
    load_accepted_documents,
    unlocated_inventory_sections,
)
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import MarkdownNormalizer
from knowledge_assistant.infrastructure.parsing.markdown_parser import MarkdownParser

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "corpus" / "manifest.json"
INVENTORY = ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
NORMALIZED = ROOT / "data" / "processed" / "documents" / "normalized.jsonl"
BLUEPRINTS = ROOT / "data" / "evaluation" / "questions" / "blueprint.yaml"
SCRIPT = ROOT / "scripts" / "ingestion" / "normalize_corpus.py"
EXCLUDED_IDS = {"14", "19", "24", "27"}


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location("normalize_corpus_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def records(script):
    return script.build()


def test_only_the_24_accepted_documents_are_loaded():
    ids = [d.source_id for d in load_accepted_documents(MANIFEST, ROOT)]
    assert len(ids) == 24 and not set(ids) & (EXCLUDED_IDS | {"25"})


def test_excluded_documents_are_never_opened(monkeypatch):
    opened = []

    class RecordingParser(MarkdownParser):
        def parse(self, document):
            opened.append(Path(document.path))
            return super().parse(document)

    NormalizeCorpus(lambda _ext: RecordingParser(), MarkdownNormalizer()).run(load_accepted_documents(MANIFEST, ROOT))
    assert len(opened) == 24
    assert all(path.parent == ROOT / "corpus" / "sources" for path in opened)


def test_manifest_listing_an_excluded_document_as_accepted_is_refused(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["documents"].append({**manifest["excluded"][0], "title": "x"})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="excluded"):
        load_accepted_documents(path, ROOT)


def test_two_runs_give_identical_hashes_and_match_the_committed_file(script, records):
    again = script.build()
    assert [r["sha256"] for r in records] == [r["sha256"] for r in again]
    committed = [json.loads(line) for line in NORMALIZED.read_text(encoding="utf-8").splitlines()]
    assert committed == records


def test_every_inventory_heading_path_has_a_span_in_the_normalized_text(records):
    inventory = [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines() if line]
    assert len(inventory) == 636
    assert unlocated_inventory_sections(records, inventory) == []


def test_every_evidence_quote_survives_normalization_inside_its_section(records):
    """Normalization must not remove ground truth: each EVAL-001 quote is still inside a span of its heading path."""
    def squash(text):
        return re.sub(r"\s+", " ", text).strip()

    by_path = {}
    for record in records:
        for section in record["metadata"]["sections"]:
            body = squash(record["text"][section["char_start"] : section["char_end"]])
            by_path.setdefault((record["id"], section["heading_path"]), []).append(body)
    blueprints = yaml.safe_load(BLUEPRINTS.read_text(encoding="utf-8"))["blueprints"]
    quotes = [(b["id"], e) for b in blueprints for e in b["ground_truth"]["evidence"]]
    assert quotes
    for blueprint_id, evidence in quotes:
        bodies = by_path[(evidence["source_id"], evidence["heading_path"])]
        assert any(squash(evidence["quote"]) in body for body in bodies), (blueprint_id, evidence["quote"][:60])


def test_normalization_removes_the_wrapper_from_every_document(records):
    for record in records:
        assert record["text"].startswith("# " + record["metadata"]["document_name"] + "\n"), record["id"]
        assert record["metadata"]["source_url"].startswith("https://"), record["id"]
        assert "requires authorization" not in record["text"], record["id"]
