# Ingestion architecture

Format-independent. Parsers live in `infrastructure/parsing` (base, markdown_parser, pdf_parser, html_parser, registry) and produce a normalized `ParsedDocument`.

## Accepted design (ADR-0002, not yet implemented)
- A MarkItDown adapter converts PDF/HTML/txt/other to Markdown; the registry picks the parser by file type. `pdf_parser.py` / `html_parser.py` placeholders will delegate to it (or be replaced by a single adapter; decide at implementation).
- Chunkers in `infrastructure/chunking/`: `header_chunker` (baseline) and `fixed_size_chunker` (experiment), both implementing `core.interfaces.chunker`.
- `markitdown` is imported only inside `infrastructure/`.

```
file -> ParserRegistry -> (MarkItDown | Markdown reader) -> ParsedDocument -> Chunker -> DocumentChunk[]
```

Current corpus is Markdown, so MarkItDown is needed only once other formats are added.
