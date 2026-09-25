# Ingestion specification

Status: decisions accepted (ADR-0002, ADR-0003). Parsing (Markdown) and normalization implemented (INGEST-001); chunking not implemented.

## Parsing
- Inputs: Markdown (current corpus), and PDF, HTML, txt and other formats via MarkItDown.
- Non-Markdown inputs are converted to Markdown by a MarkItDown adapter in `infrastructure/parsing/`, selected through `ParserRegistry`. Markdown files may be read directly.
- Output is a format-independent `ParsedDocument` (source_id, document_name, Markdown text, metadata). Nothing downstream may depend on the original format.
- Conversion failures MUST raise a clear error and MUST NOT silently drop a document.
- Conversion quality per format MUST be spot-checked before that format is used in evaluation.

## Normalization (ADR-0003 D1, both chunkers)
- In-memory step between parsing and chunking; sources are never edited.
- Wrapper H1 title and `Source:` URL move to metadata; wrapper lines and known boilerplate lines are removed.
- Version variants inside a doc are kept (variant 1..n, no guessed version labels); exact-duplicate chunks within a doc (normalized-text hash) are dropped after chunking.

## Chunking (baseline: header-aware)
- Split on H2 and H3 (H4+ stays in its parent); heading path root is the page's own H1; each `DocumentChunk` records its heading path as the citation location (`location_type` = heading).
- Sizes in characters: max 1,600, min 400; small sections merge with the next section under the same parent.
- Oversized sections split at paragraph, then sentence boundaries; code blocks and tables are atomic unless a single block exceeds the max; 200-char overlap only between pieces of one split section.
- Embedded text = heading path line + chunk text, with Markdown links reduced to their text; display text keeps the original.
- Documents without headings: fall back to paragraph/size splitting; location type then falls back to document-relative position.
- Chunks MUST keep `source_id` and `document_name`. Chunk ID = `{source_id}:{chunker_config}:{index:04d}`; metadata fields per ADR-0003 D6.
- Chunker is behind `core/interfaces/chunker.py`; the fixed-size chunker (1,600 chars, 200 overlap, same normalization and header) is a second implementation for the experiment.

## Out of scope for this spec
Embedding provider, vector store schema, retrieval (see retrieval-spec).

## Open
None for chunking. Query language = English + Vietnamese (ADR-0003 D9); it does not change chunking rules.
