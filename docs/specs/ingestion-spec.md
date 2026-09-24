# Ingestion specification

Status: decisions accepted (ADR-0002); details marked TBD. Not implemented.

## Parsing
- Inputs: Markdown (current corpus), and PDF, HTML, txt and other formats via MarkItDown.
- Non-Markdown inputs are converted to Markdown by a MarkItDown adapter in `infrastructure/parsing/`, selected through `ParserRegistry`. Markdown files may be read directly.
- Output is a format-independent `ParsedDocument` (source_id, document_name, Markdown text, metadata). Nothing downstream may depend on the original format.
- Conversion failures MUST raise a clear error and MUST NOT silently drop a document.
- Conversion quality per format MUST be spot-checked before that format is used in evaluation.

## Chunking (baseline: header-aware)
- Split on Markdown headings (levels TBD); each `DocumentChunk` records its heading path (e.g. `H1 > H2`) as the citation location (`location_type` = heading).
- Small sections merged, oversized sections split (paragraph boundary first, then size). Min/max size and overlap: TBD.
- Documents without headings: fall back to paragraph/size splitting; location type then falls back to document-relative position.
- Chunks MUST keep `source_id` and `document_name`. Chunk IDs MUST be deterministic so runs are reproducible.
- Chunker is behind `core/interfaces/chunker.py`; the fixed-size chunker is a second implementation for the experiment.

## Out of scope for this spec
Embedding provider, vector store schema, retrieval (see retrieval-spec).

## Open
Size limits, overlap, heading levels, exact fixed-size comparison values.
