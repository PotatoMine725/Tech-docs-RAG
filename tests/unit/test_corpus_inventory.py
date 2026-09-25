"""Data tests for corpus/manifest.json and the section inventory (EPIC-01, gate G1)."""
import hashlib
import json
from pathlib import Path

from knowledge_assistant.infrastructure.chunking.markdown_structure import read_page_frame, split_sections

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "corpus" / "sources"
MANIFEST = ROOT / "corpus" / "manifest.json"
INVENTORY = ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
SNAPSHOT = ROOT / "docs" / "snapshots" / "corpus" / "source-checksums-premigration.sha256"
EXCLUDED_IDS = {"14", "19", "24", "27"}


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _inventory() -> list[dict]:
    return [json.loads(line) for line in INVENTORY.read_text(encoding="utf-8").splitlines() if line]


def _source_files() -> dict[str, Path]:
    return {p.name.split("-")[0]: p for p in sorted(SOURCES.glob("*.md"))}


def _lf_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def test_manifest_lists_exactly_the_24_accepted_sources():
    ids = [doc["source_id"] for doc in _manifest()["documents"]]
    assert ids == sorted(_source_files())
    assert len(ids) == 24
    assert not set(ids) & (EXCLUDED_IDS | {"25"})


def test_manifest_records_excluded_ids_and_the_missing_25():
    manifest = _manifest()
    assert {doc["source_id"] for doc in manifest["excluded"]} == EXCLUDED_IDS
    assert manifest["never_existed_ids"] == ["25"]
    assert manifest["counts"] == {"original": 28, "accepted": 24, "excluded": 4}


def test_every_excluded_document_has_a_reason():
    for doc in _manifest()["excluded"]:
        assert doc["reason"] and "TBD" not in doc["reason"], doc["source_id"]


def test_manifest_hashes_match_the_files_on_disk():
    files = _source_files()
    for doc in _manifest()["documents"]:
        assert hashlib.sha256(_lf_bytes(files[doc["source_id"]])).hexdigest() == doc["sha256_lf"], doc["source_id"]


def test_sources_are_unchanged_since_the_premigration_snapshot():
    # The snapshot hashed the original CRLF files; rebuild CRLF from the LF text so this works on any checkout.
    snapshot = {}
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(" ", 1)
        snapshot[name.lstrip("*")] = digest
    for path in _source_files().values():
        crlf = _lf_bytes(path).replace(b"\n", b"\r\n")
        assert hashlib.sha256(crlf).hexdigest() == snapshot[path.name], path.name


def test_inventory_matches_a_fresh_computation_for_all_24_documents():
    expected = []
    for source_id, path in _source_files().items():
        lines = path.read_text(encoding="utf-8").split("\n")
        frame = read_page_frame(lines)
        for section in split_sections(lines, start_line=frame.page_title_line):
            expected.append((source_id, list(section.heading_path), section.start_line + 1, section.end_line))
    actual = [(r["source_id"], r["heading_parts"], r["line_start"], r["line_end"]) for r in _inventory()]
    assert actual == expected
    assert {r["source_id"] for r in _inventory()} == set(_source_files())
