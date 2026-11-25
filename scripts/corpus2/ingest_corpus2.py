"""Ingest corpus 2 (ADR-0008): converted text -> Unicode NFC -> data/processed/documents-corpus2/. Offline.

Reads the accepted documents of corpus2/manifest.json from corpus2/converted/<id>.md (written by convert_corpus2.py)
and refuses any whose text no longer matches the pinned `converted_sha256`. Each text is composed to NFC (owner
decision 2026-11-25; C2-07, C2-08 and C2-25 are stored NFD) and its H1-H3 sections recomputed on the NFC text. The
corpus-1 MarkdownNormalizer is not applied: its preamble/boilerplate rules are specific to the corpus-1 web pages.
Writes (git-ignored, non-redistributable text):
- normalized.jsonl  same record shape as corpus 1; chunked by build_chunks.py --corpus corpus2;
- sections.jsonl    the frozen section inventory (corpus2/converted/sections.jsonl, incl. the whole-document /
                    preamble span "") with offsets moved onto the NFC text; used for the v2 expected spans.
Run: .venv/Scripts/python.exe scripts/corpus2/ingest_corpus2.py
"""
import hashlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.application.ingestion.normalize_corpus import to_record, write_jsonl  # noqa: E402
from knowledge_assistant.config import get_normalized_path  # noqa: E402
from knowledge_assistant.core.models import Document, ParsedDocument  # noqa: E402
from knowledge_assistant.infrastructure.parsing.markdown_normalizer import section_spans  # noqa: E402
from knowledge_assistant.infrastructure.parsing.nfc_normalizer import NfcNormalizer, to_nfc  # noqa: E402

CORPUS = "corpus2"
MANIFEST = PROJECT_ROOT / "corpus2" / "manifest.json"
CONVERTED = PROJECT_ROOT / "corpus2" / "converted"


def nfc_inventory(converted_inventory: list[dict], texts: dict[str, str]) -> list[dict]:
    """The frozen section inventory (corpus2/converted/sections.jsonl, which the v2 ground truth was validated
    against) with its offsets moved onto the NFC text: offset' = len(NFC(text[:offset])). The spans themselves are
    kept as frozen, e.g. C2-22 (.md, read without sections at conversion) keeps its single whole-document "" span."""
    moved = []
    for span in converted_inventory:
        raw = texts[span["source_id"]]
        moved.append({**span, "char_start": len(to_nfc(raw[:span["char_start"]])),
                      "char_end": len(to_nfc(raw[:span["char_end"]]))})
    return moved


def build() -> tuple[list[dict], list[str], dict[str, str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    normalizer = NfcNormalizer()
    records, changed, raw_texts = [], [], {}
    for entry in manifest["documents"]:
        if entry["status"] != "accepted":
            continue
        path = CONVERTED / f"{entry['id']}.md"
        text = path.read_text(encoding="utf-8")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != entry["converted_sha256"]:
            raise SystemExit(f"{entry['id']}: converted text differs from converted_sha256; run convert_corpus2.py")
        raw_texts[entry["id"]] = text
        raw = ParsedDocument(Document(entry["id"], entry["title"], str(path)), text, document_name=entry["title"],
                             sections=section_spans(text))
        parsed = normalizer.normalize(raw)
        if parsed is not raw:
            changed.append(f"{entry['id']} ({len(text) - len(parsed.text)} chars shorter)")
        records.append(to_record(parsed, path.relative_to(PROJECT_ROOT).as_posix()))
    return records, changed, raw_texts


def main() -> int:
    records, changed, raw_texts = build()
    output = get_normalized_path(CORPUS)
    write_jsonl(records, output)
    frozen = [json.loads(line) for line in (CONVERTED / "sections.jsonl").read_text(encoding="utf-8").splitlines() if line]
    spans = nfc_inventory(frozen, raw_texts)
    nfc_texts = {r["id"]: r["text"] for r in records}
    bad = [new for old, new in zip(frozen, spans)
           if to_nfc(raw_texts[old["source_id"]][old["char_start"]:old["char_end"]])
           != nfc_texts[new["source_id"]][new["char_start"]:new["char_end"]]]
    if bad:  # the moved span must hold exactly the NFC form of the frozen span's text
        raise SystemExit(f"{len(bad)} moved spans do not match the NFC text, e.g. {bad[0]}")
    write_jsonl(spans, output.with_name("sections.jsonl"))
    print(f"{len(records)} documents, {sum(len(r['text']) for r in records):,} chars, {len(spans)} sections")
    print(f"composed to NFC: {', '.join(changed) or 'none'}")
    print(f"wrote {output.relative_to(PROJECT_ROOT).as_posix()} and sections.jsonl")
    return 0


if __name__ == "__main__":
    sys.exit(main())
