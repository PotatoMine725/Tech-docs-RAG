"""Convert corpus 2 (ADR-0008) with the existing MarkItDown parser and refresh the measured manifest fields. Offline.

Reads corpus2/manifest.json (committed; curated fields are edited by hand), the raw files in corpus2/incoming/ and
writes, git-ignored:
- corpus2/converted/<id>.md        converted text of every accepted document;
- corpus2/converted/sections.jsonl the section inventory used by the v2 question validator: H1-H3 spans as for
  corpus 1, plus one whole-document span (heading_path "") for documents without headings.
Measured fields written back into the manifest: sha256, bytes, pages, image_count, has_images, chars, headings,
converted_sha256 (the converted text) and, at the top, the converter library versions. --check fails when the
converted text no longer matches converted_sha256 (e.g. after a library upgrade): frozen quotes depend on it.
Files in incoming/ that the manifest does not list are reported and get the next free ID with status "pending".
Converting is not indexing: no chunks, embeddings or vector store are built here.

Run: .venv/Scripts/python.exe scripts/corpus2/convert_corpus2.py [--check]   (--check: verify only, write nothing)
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.core.models import Document  # noqa: E402
from knowledge_assistant.infrastructure.parsing.registry import default_registry  # noqa: E402

CORPUS2 = PROJECT_ROOT / "corpus2"
MANIFEST = CORPUS2 / "manifest.json"
INCOMING = CORPUS2 / "incoming"
CONVERTED = CORPUS2 / "converted"
SECTIONS = CONVERTED / "sections.jsonl"
ID_FORMAT = "C2-{:02d}"
MEASURED = ("sha256", "bytes", "pages", "image_count", "has_images", "chars", "headings", "converted_sha256")
LIBRARIES = ("markitdown", "pdfminer.six", "mammoth", "python-pptx")


def library_versions() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    found = {}
    for name in LIBRARIES:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            found[name] = None
    return found


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pdf_pages_and_images(path: Path) -> tuple[int, int]:
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdftypes import resolve1

    pages = images = 0
    with path.open("rb") as handle:
        for page in PDFPage.get_pages(handle):
            pages += 1
            xobjects = resolve1((page.resources or {}).get("XObject")) or {}
            for ref in xobjects.values():
                obj = resolve1(ref)
                if getattr(obj, "attrs", {}).get("Subtype") is not None and \
                        resolve1(obj.attrs["Subtype"]).name == "Image":
                    images += 1
    return pages, images


def _office_pages_and_images(path: Path) -> tuple[int | None, int]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        images = sum(1 for n in names if re.match(r"(word|ppt)/media/", n))
        if path.suffix.lower() == ".pptx":
            return sum(1 for n in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), images
        app = archive.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in names else ""
        match = re.search(r"<Pages>(\d+)</Pages>", app)  # as last saved by Word; null when absent
        return (int(match.group(1)) if match else None), images


def pages_and_images(path: Path, text: str) -> tuple[int | None, int]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_pages_and_images(path)
    if suffix in (".docx", ".pptx"):
        return _office_pages_and_images(path)
    return None, len(re.findall(r"!\[", text))  # .md / .txt: no pages


def sections(source_id: str, parsed) -> list[dict]:
    spans = [{"source_id": source_id, "heading_path": " > ".join(s.heading_path), "variant": s.variant,
              "char_start": s.char_start, "char_end": s.char_end} for s in parsed.sections]
    if not spans or spans[0]["char_start"] > 0:  # text before the first heading, or no headings at all
        spans.insert(0, {"source_id": source_id, "heading_path": "", "variant": 1, "char_start": 0,
                         "char_end": spans[0]["char_start"] if spans else len(parsed.text)})
    return spans


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    args.add_argument("--check", action="store_true", help="verify hashes and conversion; write nothing")
    check = args.parse_args().check
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_file = {d["file"]: d for d in manifest["documents"]}
    errors, warnings, inventory = [], [], []
    for path in sorted(INCOMING.iterdir()) if INCOMING.is_dir() else []:
        if path.name not in by_file:
            used = [int(d["id"].split("-")[1]) for d in manifest["documents"]]
            entry = {"id": ID_FORMAT.format(max(used, default=0) + 1), "file": path.name, "status": "pending"}
            manifest["documents"].append(entry)
            by_file[path.name] = entry
            print(f"NEW {entry['id']} {path.name} (status pending: curate in the manifest)")
    registry = default_registry()
    for doc in manifest["documents"]:
        path = INCOMING / doc["file"]
        if not path.is_file():
            errors.append(f"{doc['id']}: raw file missing: {doc['file']}")
            continue
        digest = sha256(path)
        if doc.get("sha256") and doc["sha256"] != digest:
            errors.append(f"{doc['id']}: sha256 changed (the raw file was edited or replaced)")
        doc["sha256"], doc["bytes"] = digest, path.stat().st_size
        if doc["status"] != "accepted":
            continue
        try:
            parsed = registry.get(path.suffix).parse(Document(doc["id"], path.stem, str(path)))
        except Exception as error:  # report every failing file, not just the first
            errors.append(f"{doc['id']}: {error}")
            continue
        doc["pages"], doc["image_count"] = pages_and_images(path, parsed.text)
        doc["has_images"] = doc["image_count"] > 0
        doc["chars"], doc["headings"] = len(parsed.text), len(parsed.sections)
        converted = hashlib.sha256(parsed.text.encode("utf-8")).hexdigest()
        if doc.get("converted_sha256") and doc["converted_sha256"] != converted:
            (errors if check else warnings).append(f"{doc['id']}: converted text changed (converter output differs)")
        doc["converted_sha256"] = converted
        inventory += sections(doc["id"], parsed)
        if not check:
            CONVERTED.mkdir(parents=True, exist_ok=True)
            (CONVERTED / f"{doc['id']}.md").write_text(parsed.text, encoding="utf-8", newline="\n")
    if check and manifest.get("converter") and manifest["converter"] != library_versions():
        warnings.append(f"converter libraries differ from the manifest: {library_versions()}")
    if not check:
        manifest["converter"] = library_versions()
        with SECTIONS.open("w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in inventory)
        with MANIFEST.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    accepted = sum(d["status"] == "accepted" for d in manifest["documents"])
    print(f"{len(manifest['documents'])} documents, {accepted} accepted, {len(inventory)} sections")
    for warning in warnings:
        print(f"WARNING {warning}")
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
