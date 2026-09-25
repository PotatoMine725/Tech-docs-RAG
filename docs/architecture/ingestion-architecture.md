# Ingestion architecture

Format-independent. Parsers live in `infrastructure/parsing` (base, markdown_parser, pdf_parser, html_parser, registry) and produce a normalized `ParsedDocument`.

## Accepted design (ADR-0002, not yet implemented)
- A MarkItDown adapter converts PDF/HTML/txt/other to Markdown; the registry picks the parser by file type. `pdf_parser.py` / `html_parser.py` placeholders will delegate to it (or be replaced by a single adapter; decide at implementation).
- Chunkers in `infrastructure/chunking/`: header-aware (baseline) and fixed-size (experiment), both implementing `core.interfaces.chunker` (implemented in INGEST-002, see below).
- `markitdown` is imported only inside `infrastructure/`.

```
file -> ParserRegistry -> (MarkItDown | Markdown reader) -> ParsedDocument (raw) -> MarkdownNormalizer (D1) -> ParsedDocument (normalized) -> Chunker -> DocumentChunk[]
```

Current corpus is Markdown, so MarkItDown is needed only once other formats are added.

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
