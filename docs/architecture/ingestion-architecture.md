# Ingestion architecture

Format-independent. Parsers live in `infrastructure/parsing` (base, markdown_parser, markitdown_parser, registry) and produce a `ParsedDocument` whose text is Markdown.

## Accepted design (ADR-0002; MarkItDown adapter implemented in INGEST-003)
- A MarkItDown adapter converts PDF/HTML/DOCX/txt to Markdown; the registry picks the parser by file type.
- **OD-6 resolved (INGEST-003, 2026-09-25, AI decision while the owner was away; see the INGEST-003 report):** one shared adapter, `markitdown_parser.py`, registered for every MarkItDown extension. The `pdf_parser.py` / `html_parser.py` stubs were deleted (empty skeletons, no importers). Reason: MarkItDown already dispatches by format, so per-format wrappers would be empty pass-throughs.
- Chunkers in `infrastructure/chunking/`: header-aware (baseline) and fixed-size (experiment), both implementing `core.interfaces.chunker` (implemented in INGEST-002, see below).
- `markitdown` is imported only by `infrastructure/parsing/markitdown_parser.py` (structure test).

```
file -> ParserRegistry -> (MarkItDown | Markdown reader) -> ParsedDocument (raw) -> MarkdownNormalizer (D1) -> ParsedDocument (normalized) -> Chunker -> DocumentChunk[]
```

Current corpus is Markdown, so MarkItDown is needed only once other formats are added.

## Implemented (INGEST-003)
- `infrastructure/parsing/markitdown_parser.py` (`MarkItDownParser`, `MARKITDOWN_EXTENSIONS` = `.pdf .html .htm .docx .txt`): `markitdown` is imported lazily on the first `parse`, so `default_registry()` does not load it (and its `magika`/`onnxruntime` dependencies) for the Markdown corpus.
- Output: raw `ParsedDocument` (`normalized=False`) with LF line endings, `document_name` = the converter's title (HTML `<title>`) or `Document.name`, and `sections` from `section_spans` (the same H1–H3 spans the normalizer computes). The ADR-0003 D1 `MarkdownNormalizer` is **not** applied: it requires the web-export page frame (wrapper H1 + page H1) and raises on anything else. So for converted files the flow is `file -> ParserRegistry -> MarkItDownParser -> ParsedDocument -> Chunker`.
- `.pdf` and `.docx` are checked against their file signature before conversion: MarkItDown guesses the converter from the content and returned a damaged `.docx` as its raw bytes read as plain text. Any conversion failure raises `DocumentParseError`.
- Known limits: plain PDF text has no Markdown headings, so it has no sections and chunks get an empty heading path (`location_type` stays `heading`; the `position` type of `Citation` is not produced yet). Conversion quality of real PDFs/tables is unchecked (no such inputs in the corpus).

## Implemented (INGEST-001)
- `infrastructure/parsing/markdown_parser.py` reads the file unchanged (line endings kept); `registry.default_registry()` maps `.md`/`.markdown` to it.
- `infrastructure/parsing/markdown_normalizer.py` implements `core.interfaces.normalizer.DocumentNormalizer`: CRLF → LF first; everything before the page H1 goes to metadata or is dropped (unknown preamble lines raise `DocumentParseError`); `BOILERPLATE_LINES` removed outside code fences; blank-line runs collapsed; `SectionSpan`s computed with `markdown_structure.split_sections`.
- `application/ingestion/normalize_corpus.py` (`NormalizeCorpus`, depends on core interfaces only) + `scripts/ingestion/normalize_corpus.py` → `data/processed/documents/normalized.jsonl` (one line per doc: `id`, `metadata` incl. section spans, `text`, `sha256`). The script exits 1 if any section-inventory heading path has no span.

## Implemented (INGEST-002)
- `infrastructure/chunking/header_aware.py` (Arm A) and `fixed_size.py` (Arm B) only decide spans (char range + heading path). `chunk_builder.py` turns spans into `DocumentChunk`s for both arms (D5 embed text, D6 ID, per-document duplicate drop), so both arms emit identical fields.
- `infrastructure/chunking/factory.py` builds an arm from `config/chunking.json`; `stats.py` computes the D8 descriptive stats.
- `application/ingestion/build_chunks.py` (core only): `normalized.jsonl` → `ParsedDocument`s (`from_record`), chunk → D6 record.
- `scripts/ingestion/build_chunks.py --arm A|B` → `data/processed/chunks/arm-{a,b}.jsonl` + `stats-arm-{a,b}.json`; `scripts/ingestion/check_g2.py` → `validation/ingestion/g2-check.md`.

```
normalized.jsonl -> from_record -> ParsedDocument -> HeaderAwareChunker | FixedSizeChunker -> Span[] -> build_chunks -> DocumentChunk[] -> arm-*.jsonl
```
