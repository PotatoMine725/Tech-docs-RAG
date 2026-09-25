# Ingestion architecture

Format-independent. Parsers live in `infrastructure/parsing` (base, markdown_parser, pdf_parser, html_parser, registry) and produce a normalized `ParsedDocument`.

## Accepted design (ADR-0002, not yet implemented)
- A MarkItDown adapter converts PDF/HTML/txt/other to Markdown; the registry picks the parser by file type. `pdf_parser.py` / `html_parser.py` placeholders will delegate to it (or be replaced by a single adapter; decide at implementation).
- Chunkers in `infrastructure/chunking/`: `header_chunker` (baseline) and `fixed_size_chunker` (experiment), both implementing `core.interfaces.chunker`.
- `markitdown` is imported only inside `infrastructure/`.

```
file -> ParserRegistry -> (MarkItDown | Markdown reader) -> ParsedDocument (raw) -> MarkdownNormalizer (D1) -> ParsedDocument (normalized) -> Chunker -> DocumentChunk[]
```

Current corpus is Markdown, so MarkItDown is needed only once other formats are added.

## Implemented (INGEST-001)
- `infrastructure/parsing/markdown_parser.py` reads the file unchanged (line endings kept); `registry.default_registry()` maps `.md`/`.markdown` to it.
- `infrastructure/parsing/markdown_normalizer.py` implements `core.interfaces.normalizer.DocumentNormalizer`: CRLF → LF first; everything before the page H1 goes to metadata or is dropped (unknown preamble lines raise `DocumentParseError`); `BOILERPLATE_LINES` removed outside code fences; blank-line runs collapsed; `SectionSpan`s computed with `markdown_structure.split_sections`.
- `application/ingestion/normalize_corpus.py` (`NormalizeCorpus`, depends on core interfaces only) + `scripts/ingestion/normalize_corpus.py` → `data/processed/documents/normalized.jsonl` (one line per doc: `id`, `metadata` incl. section spans, `text`, `sha256`). The script exits 1 if any section-inventory heading path has no span.
