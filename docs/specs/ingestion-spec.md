# Ingestion specification

Status: decisions accepted (ADR-0002, ADR-0003). Parsing (Markdown) and normalization implemented (INGEST-001); both chunkers implemented (INGEST-002).

## Parsing
- Inputs: Markdown (current corpus), and PDF, HTML, txt and other formats via MarkItDown.
- Non-Markdown inputs are converted to Markdown by a MarkItDown adapter in `infrastructure/parsing/`, selected through `ParserRegistry`. Markdown files may be read directly.
- Output is a format-independent `ParsedDocument` (source_id, document_name, Markdown text, metadata). Nothing downstream may depend on the original format.
- Conversion failures MUST raise a clear error and MUST NOT silently drop a document.
- Conversion quality per format MUST be spot-checked before that format is used in evaluation.

## Normalization (ADR-0003 D1, both chunkers)
- In-memory step between parsing and chunking; sources are never edited.
- Wrapper H1 title and `Source:` URL move to metadata; wrapper lines and known boilerplate lines are removed.
- Removal list as implemented (INGEST-001; the single list with sources is the REMOVAL LIST block in `infrastructure/parsing/markdown_normalizer.py`):
  - preamble before the page H1: wrapper H1, `Source:`, `---`, "Note", the access lines (EPIC-01, ADR-0003), #29 YAML front matter (EPIC-01); an unknown preamble line raises an error;
  - body, outside code fences: access lines (EPIC-01, ADR-0003); "This isn't the latest version…", "…no longer supported…", author bylines `By [Name](url)` (ADR-0003); the admonition label introducing one of these;
  - **extension beyond ADR-0003 D1 (INGEST-001, confirmed by the owner 2026-09-25):** the page footer `- Last updated on` + its date line + the `---` before it (19 docs). It is page chrome (edit date), carries no content, and no evidence quote uses it.
  - ADR-0003's "version-selector lines": searched for, none exist in the corpus (the tab-selector link lists in #12 are content and are kept).
  - Known residue, kept (owner decision 2026-09-25; the #15 `##` lines are real headings in the section inventory): `---` before "## Additional resources" (20 docs); #15's Q&A page text ("Sign in to comment", "No comments").
- Version variants inside a doc are kept (variant 1..n, no guessed version labels); exact-duplicate chunks within a doc (normalized-text hash) are dropped after chunking.

## Chunking (baseline: header-aware)
- Split on H2 and H3 (H4+ stays in its parent); heading path root is the page's own H1; each `DocumentChunk` records its heading path as the citation location (`location_type` = heading).
- Sizes in characters: max 1,600, min 400; small sections merge with the next section under the same parent.
- Oversized sections split at paragraph, then sentence boundaries; code blocks and tables are atomic unless a single block exceeds the max; 200-char overlap only between pieces of one split section.
- Embedded text = heading path line + chunk text, with Markdown links reduced to their text; display text keeps the original.
- Documents without headings: fall back to paragraph/size splitting; location type then falls back to document-relative position.
- Chunks MUST keep `source_id` and `document_name`. Chunk ID = `{source_id}:{chunker_config}:{index:04d}`; metadata fields per ADR-0003 D6.
- Chunker is behind `core/interfaces/chunker.py`; the fixed-size chunker (1,600 chars, 200 overlap, same normalization and header) is a second implementation for the experiment.

## As implemented (INGEST-002)
- Parameters live in `config/chunking.json` (Arm A `header-1600`, Arm B `fixed-1600`); these names are the `chunker_config` part of the chunk ID.
- `display_text` is always the exact slice `normalized_text[char_start:char_end]` (leading/trailing whitespace trimmed), for both arms.
- **Table split (owner decision 2026-09-25):** when a table longer than 1,600 chars is split by rows, the header row (+ separator row) is repeated in `embed_text` only, not in `display_text`, so the slice rule above holds for every chunk.
- Interpretations of ADR-0003 (no parameter changed):
  - D3 merge: a section under 400 chars merges with the *immediately following* section only if it is a sibling (same parent heading path and level) and the merged text is at most 1,600 chars; repeated while still under 400. A parent section followed by its own child never merges, so an H2 directly followed by H3s becomes a heading-only chunk (19 in Arm A).
  - D4 split: blocks = paragraphs, fenced code, tables, heading lines. Blocks up to 1,600 chars are never cut. A longer block is cut into sub-blocks of at most 1,400 chars (max − overlap) — code by lines, tables by rows, paragraphs by sentences, then at a space. A heading at the end of a piece moves to the next piece.
  - D4 overlap: up to 200 chars from the end of the previous piece of the same section, reduced so the piece stays ≤ 1,600; it starts at a word boundary, at a row start inside a table, and never inside a code fence.
  - D5: `embed_text` = heading path joined with " > " + blank line + chunk text with `[text](url)` / `![alt](url)` → `text` outside code fences.
  - D1 duplicate drop: SHA-256 of `display_text`, per document, before IDs are numbered (IDs stay contiguous).
  - Arm B windows start every 1,400 chars; heading path = the H1–H3 section that contains the (trimmed) chunk start.

## Out of scope for this spec
Embedding provider, vector store schema, retrieval (see retrieval-spec).

## Open
- Heading-only / small Arm A chunks (19 heading-only, 79 under 400 chars): keep as ADR-0003 D3 says, or amend D3 to let a small parent merge into its first child. Needs an owner decision + ADR amendment; not changed by INGEST-002.
- Otherwise none for chunking. Query language = English + Vietnamese (ADR-0003 D9); it does not change chunking rules.
